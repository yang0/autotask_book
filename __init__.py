from .shuba import *


VERSION = "0.0.2"
GIT_URL = "https://github.com/yang0/autotask_book.git"
NAME = "AutoTask Book"
DESCRIPTION = """AutoTask Book 是一个小说下载插件，提供以下功能：

• 小说下载节点
  - 69书吧小说下载：支持从69shuba.com下载小说章节
  - 自动处理章节顺序：支持正序和倒序章节的自动处理
  - 智能重试机制：自动处理网络错误和重试
  - 断点续传：支持中断后继续下载
  - 章节去广告：自动清理章节内容中的广告和无关内容

• 文件管理
  - 自动创建小说目录
  - 按章节编号保存文件
  - 支持UTF-8和GBK编码
  - 自动跳过已下载章节

• 错误处理
  - 详细的错误日志
  - 友好的错误提示
  - 网络异常自动重试
  - 支持用户中断下载

使用此插件可以方便地下载和管理小说内容，支持批量下载和断点续传。"""

TAGS = ["book", "novel", "download", "69shuba"]
