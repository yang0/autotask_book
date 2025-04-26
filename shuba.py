try:
    from autotask.nodes import Node, register_node
except ImportError:
    from stub import Node, register_node

from typing import Dict, Any, AsyncGenerator
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@register_node
class NovelDownloadNode(Node):
    NAME = "69shuba Novel Download"
    DESCRIPTION = "Download novel from 69shuba.com"

    INPUTS = {
        "catalog_url": {
            "label": "Catalog URL",
            "description": "URL of the novel catalog page",
            "type": "STRING",
            "required": True
        },
        "start_chapter": {
            "label": "Start Chapter",
            "description": "Index of chapter to start from (1-based)",
            "type": "INT",
            "default": 1,
            "required": False
        },
        "end_chapter": {
            "label": "End Chapter",
            "description": "Index of chapter to end at (1-based)",
            "type": "INT",
            "default": -1,
            "required": False
        },
        "output_dir": {
            "label": "Output Directory",
            "description": "Directory to save the novel",
            "type": "STRING",
            "required": True,
            "widget": "DIR"
        }
    }

    OUTPUTS = {
        "success": {
            "label": "Success",
            "description": "Whether the download was successful",
            "type": "BOOLEAN"
        },
        "error_message": {
            "label": "Error Message",
            "description": "Error message if download failed",
            "type": "STRING"
        },
        "novel_dir": {
            "label": "Novel Directory",
            "description": "Directory where the novel chapters are saved",
            "type": "STRING"
        },
        "novel_file": {
            "label": "Novel File",
            "description": "Path to the combined novel file (output_dir + novel_title + .txt)",
            "type": "STRING"
        }
    }

    def __init__(self):
        super().__init__()
        # Configure retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4, 8, 16 seconds between retries
            status_forcelist=[500, 502, 503, 504, 429],  # HTTP status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.4472.124 Safari/537.36'
        })
        self._stop_flag = False

    def _fetch_catalog(self, catalog_url: str, workflow_logger) -> Dict[str, Any]:
        """Fetch novel catalog and return novel info"""
        try:
            workflow_logger.info(f"Fetching catalog from: {catalog_url}")
            
            response = self.session.get(catalog_url, timeout=30)
            response.encoding = 'gbk'

            if response.status_code != 200:
                error_msg = f"Failed to fetch catalog, status code: {response.status_code}"
                workflow_logger.error(error_msg)
                return {"success": False, "error_message": error_msg}

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get novel title
            bread_div = soup.find('div', class_='bread')
            if not bread_div:
                error_msg = "Could not find bread div"
                workflow_logger.error(error_msg)
                return {"success": False, "error_message": error_msg}
            
            title_links = bread_div.find_all('a')
            if not title_links:
                error_msg = "Could not find title links"
                workflow_logger.error(error_msg)
                return {"success": False, "error_message": error_msg}
            
            title = title_links[-1].text
            workflow_logger.info(f"Found novel title: {title}")
            
            # Get chapter list
            chapter_list = []
            uls = soup.find_all('ul')
            if len(uls) >= 2:
                chapter_ul = uls[1]  # Use the second ul which contains chapter links
                chapter_links = chapter_ul.find_all('a')
                for a in chapter_links:
                    chapter_list.append(a["href"])
            else:
                error_msg = f"Could not find chapter list ul (found {len(uls)} uls)"
                workflow_logger.error(error_msg)
                return {"success": False, "error_message": error_msg}
            
            # Check sorting order from the page
            is_reverse_order = False
            sorting_div = soup.find('div', class_='sorting')
            if sorting_div:
                # If "正序" is hidden and "倒序" is visible, it means chapters are in reverse order
                small_to_big = sorting_div.find('a', onclick='smallToBig()')
                big_to_small = sorting_div.find('a', onclick='bigToSmall()')
                if small_to_big and big_to_small:
                    if small_to_big.get('style') == 'display:none' and 'display:none' not in big_to_small.get('style', ''):
                        is_reverse_order = True
                        workflow_logger.info("Detected reverse chapter order from sorting buttons")
            
            # Create novel info structure
            novel_info = {
                "title": title,
                "catalog_url": catalog_url,
                "chapters": chapter_list,
                "is_reverse_order": is_reverse_order
            }

            workflow_logger.info(f"Successfully fetched catalog for: {title}")
            return {
                "success": True,
                "novel_info": novel_info
            }

        except Exception as e:
            error_msg = f"Catalog fetch failed: {str(e)}"
            workflow_logger.error(error_msg)
            return {"success": False, "error_message": error_msg}

    def _process_chapter_content(self, content: str) -> str:
        """Process chapter content to remove unwanted elements"""
        content_lines = content.split('\n')
        start_line = 0
        end_line = len(content_lines)

        for i, line in enumerate(content_lines):
            if '<script>loadAdv(2, 0);</script>' in line:
                start_line = i + 2
            if "<script>loadAdv(3, 0);</script>" in line:
                end_line = i - 1

        processed_content = content_lines[start_line:end_line]
        processed_text = '\n'.join(processed_content)
        
        # Clean up the text
        processed_text = processed_text.replace('&emsp;&emsp;', '')  # Remove &emsp;
        processed_text = processed_text.replace('<br />', '\n')
        processed_text = processed_text.replace('<p>', '')
        processed_text = processed_text.replace('</p>', '\n')
        processed_text = processed_text.replace('最⊥新⊥小⊥说⊥在⊥六⊥9⊥⊥书⊥⊥吧⊥⊥首⊥发！', '')
        processed_text = processed_text.replace('<div class="contentadv"><script>loadAdv(7,3);</script></div>', '')
        
        # Remove extra blank lines
        lines = [line.strip() for line in processed_text.split('\n') if line.strip()]
        return '\n'.join(lines)

    def _get_chapter_file_path(self, output_dir: str, novel_title: str, chapter_index: int) -> str:
        """Get the file path for a chapter"""
        # Create directory for the novel if it doesn't exist
        # Remove "章节列表" from directory name if present
        if novel_title.endswith("章节列表"):
            novel_title = novel_title[:-4]
        novel_dir = os.path.join(output_dir, novel_title)
        if not os.path.exists(novel_dir):
            os.makedirs(novel_dir)
        return os.path.join(novel_dir, f"chapter_{chapter_index:04d}.txt")

    def _is_chapter_downloaded(self, output_dir: str, novel_title: str, chapter_index: int) -> bool:
        """Check if a chapter has already been downloaded"""
        file_path = self._get_chapter_file_path(output_dir, novel_title, chapter_index)
        return os.path.exists(file_path)

    def _download_chapter(self, chapter_url: str, chapter_index: int, output_dir: str, novel_title: str, workflow_logger) -> bool:
        """Download a single chapter and save it to file"""
        try:
            # Check if stop was requested
            if self._stop_flag:
                workflow_logger.info("Download interrupted by user request")
                return False

            # Skip if chapter already downloaded
            if self._is_chapter_downloaded(output_dir, novel_title, chapter_index):
                workflow_logger.info(f"Chapter {chapter_index} already downloaded, skipping")
                return True

            workflow_logger.info(f"Downloading chapter {chapter_index}: {chapter_url}")
            
            # Add delay between requests to avoid rate limiting
            time.sleep(2)
            
            response = self.session.get(chapter_url, timeout=30)
            response.encoding = 'gbk'

            if response.status_code != 200:
                workflow_logger.warning(f"Failed to download chapter {chapter_index}, status code: {response.status_code}")
                return False

            processed_content = self._process_chapter_content(response.text)
            
            # Save chapter to file with proper encoding
            file_path = self._get_chapter_file_path(output_dir, novel_title, chapter_index)
            try:
                with open(file_path, "w", encoding='utf-8', errors='ignore') as f:
                    f.write(processed_content)
            except UnicodeEncodeError:
                # If UTF-8 fails, try GBK encoding
                with open(file_path, "w", encoding='gbk', errors='ignore') as f:
                    f.write(processed_content)

            workflow_logger.info(f"Saved chapter {chapter_index} to: {file_path}")
            return True
            
        except requests.exceptions.SSLError as e:
            workflow_logger.error(f"SSL error downloading chapter {chapter_index}: {str(e)}")
            time.sleep(10)
            return False
        except requests.exceptions.RequestException as e:
            workflow_logger.error(f"Request error downloading chapter {chapter_index}: {str(e)}")
            time.sleep(10)
            return False
        except Exception as e:
            workflow_logger.error(f"Unexpected error downloading chapter {chapter_index}: {str(e)}")
            time.sleep(10)
            return False

    def _normalize_url(self, url: str) -> str:
        """Normalize the URL to standard format: https://www.69shuba.com/book/{id}/"""
        try:
            # Extract the book ID from the URL using regex
            import re
            match = re.search(r'book/(\d+)', url)
            if not match:
                raise ValueError("Could not find book ID in URL")
            
            book_id = match.group(1)
            return f"https://www.69shuba.com/book/{book_id}/"
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")

    def _merge_chapters(self, novel_dir: str, novel_file: str, start_chapter: int, end_chapter: int, workflow_logger) -> bool:
        """Merge all downloaded chapters into a single text file"""
        try:
            workflow_logger.info(f"Merging chapters {start_chapter} to {end_chapter} into {novel_file}")
            
            # First check if all chapter files exist
            missing_chapters = []
            for i in range(start_chapter, end_chapter + 1):
                chapter_file = os.path.join(novel_dir, f"chapter_{i:04d}.txt")
                if not os.path.exists(chapter_file):
                    missing_chapters.append(i)
            
            if missing_chapters:
                workflow_logger.warning(f"Missing chapter files: {missing_chapters}")
                return False
            
            # Now merge all chapters
            with open(novel_file, "w", encoding='utf-8', errors='ignore') as outfile:
                # Write novel title at the beginning
                outfile.write(f"{os.path.basename(novel_dir)}\n\n")
                
                for i in range(start_chapter, end_chapter + 1):
                    chapter_file = os.path.join(novel_dir, f"chapter_{i:04d}.txt")
                    with open(chapter_file, "r", encoding='utf-8', errors='ignore') as infile:
                        content = infile.read().strip()
                        if content:
                            outfile.write(content)
                            outfile.write("\n\n")
            
            workflow_logger.info(f"Successfully merged chapters into {novel_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to merge chapters: {str(e)}"
            workflow_logger.error(error_msg)
            return False

    async def execute(self, node_inputs: Dict[str, Any], workflow_logger) -> Dict[str, Any]:
        try:
            # Reset stop flag at the start of execution
            self._stop_flag = False
            
            catalog_url = node_inputs["catalog_url"]
            # Normalize the URL to standard format
            catalog_url = self._normalize_url(catalog_url)
            start_chapter = node_inputs.get("start_chapter", 1)  # 1-based
            end_chapter = node_inputs.get("end_chapter", -1)
            output_dir = node_inputs.get("output_dir", ".")
            
            # Fetch catalog
            catalog_result = self._fetch_catalog(catalog_url, workflow_logger)
            if not catalog_result["success"]:
                return catalog_result
            
            novel_info = catalog_result["novel_info"]
            if end_chapter == -1:
                end_chapter = len(novel_info["chapters"])
            
            # Adjust to 0-based index for array access
            start_idx = start_chapter - 1
            end_idx = end_chapter - 1
            
            # Adjust indices if chapters are in reverse order
            if novel_info["is_reverse_order"]:
                total_chapters = len(novel_info["chapters"])
                # For reverse order, we need to reverse the chapter list
                novel_info["chapters"] = novel_info["chapters"][::-1]
                workflow_logger.info("Reversed chapter list order")
            
            # Get novel directory path
            novel_title = novel_info["title"]
            if novel_title.endswith("章节列表"):
                novel_title = novel_title[:-4]
            novel_dir = os.path.join(output_dir, novel_title)
            
            # Get novel file path
            novel_file = os.path.join(output_dir, f"{novel_title}.txt")
            
            workflow_logger.info(f"Starting chapter download for: {novel_info['title']}")
            workflow_logger.info(f"Downloading chapters {start_chapter} to {end_chapter}")

            # Download chapters
            for i in range(start_idx, end_idx + 1):
                # Check if stop was requested
                if self._stop_flag:
                    workflow_logger.info("Download interrupted by user request")
                    return {
                        "success": False,
                        "error_message": "Download interrupted by user request",
                        "novel_dir": novel_dir,
                        "novel_file": novel_file
                    }
                
                chapter_url = novel_info["chapters"][i]
                chapter_index = i + 1  # Convert back to 1-based for display
                if not self._download_chapter(chapter_url, chapter_index, output_dir, novel_info["title"], workflow_logger):
                    return {
                        "success": False,
                        "error_message": f"Failed to download chapter {chapter_index}",
                        "novel_dir": novel_dir,
                        "novel_file": novel_file
                    }

            workflow_logger.info("All chapters downloaded, starting merge...")
            
            # Merge all chapters into a single file
            if not self._merge_chapters(novel_dir, novel_file, start_chapter, end_chapter, workflow_logger):
                return {
                    "success": False,
                    "error_message": "Failed to merge chapters",
                    "novel_dir": novel_dir,
                    "novel_file": novel_file
                }

            workflow_logger.info("Chapter download and merge completed successfully")
            return {
                "success": True,
                "error_message": "",
                "novel_dir": novel_dir,
                "novel_file": novel_file
            }

        except Exception as e:
            error_msg = f"Novel download failed: {str(e)}"
            workflow_logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg,
                "novel_dir": "",
                "novel_file": ""
            }
            
    async def stop(self) -> None:
        """
        Stop the node execution when interrupted.
        This method will set the stop flag to interrupt the download process.
        """
        self._stop_flag = True
        # Close the session to release resources
        self.session.close()

if __name__ == "__main__":
    import asyncio
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    async def test_novel_download():
        # Test download node
        download_node = NovelDownloadNode()
        result = await download_node.execute({
            "catalog_url": "https://www.69shuba.com/book/43484/",
            "start_chapter": 1,
            "end_chapter": 3,
            "output_dir": "test_output"
        }, logger)
        
        if result["success"]:
            print("Novel download completed successfully")
        else:
            print(f"Failed to download novel: {result['error_message']}")
    
    # Run the test
    asyncio.run(test_novel_download())
