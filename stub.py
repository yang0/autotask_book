from typing import Dict, Any, TypeVar, Type, Generator, List, Optional, Union
from abc import ABC, abstractmethod

def register_node(cls):
    """Development environment stub decorator"""
    return cls

class Node(ABC):
    """Base node class for development environment"""
    NAME: str = ""
    DESCRIPTION: str = ""
    CATEGORY: str = "Uncategorized"
    INPUTS: Dict[str, Dict[str, Any]] = {}
    OUTPUTS: Dict[str, Dict[str, Any]] = {}
    
    @abstractmethod
    async def execute(self, node_inputs: Dict[str, Any], workflow_logger) -> Dict[str, Any]:
        raise NotImplementedError
    

    @property
    def is_generator(self) -> bool:
        """Whether this is a generator node"""
        return False
    
    @classmethod
    def get_all_configured_agents(cls) -> List[Dict[str, Any]]:
        """get all configured agents"""
        pass

    async def run_agent(self, agent_id: str, input_text: str) -> str:
        """run agent"""
        pass

class GeneratorNode(Node):
    """Generator node base class for development environment"""
    
    @property
    def is_generator(self) -> bool:
        """Override parent's is_generator property"""
        return True
    
    @abstractmethod
    async def execute(self, node_inputs: Dict[str, Any], workflow_logger) -> Generator:
        """
        Execute the generator node
        
        Args:
            node_inputs: Input parameters dictionary
            workflow_logger: Logger instance for workflow execution
            
        Returns:
            Generator that yields results
        """
        raise NotImplementedError



class ConditionalNode(Node):
    """Conditional branch node base class for development environment"""
    
    @property
    def is_conditional(self) -> bool:
        """Whether this is a conditional branch node"""
        return True

    @abstractmethod
    def get_active_branch(self, outputs: Dict[str, Any]) -> str:
        """
        Get the name of currently active branch
        
        Args:
            outputs: Node execution outputs
            
        Returns:
            str: Name of the active output port
        """
        raise NotImplementedError


class VectorStore(ABC):
    """向量数据库抽象基类"""

    @abstractmethod
    async def batch_add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """批量添加文档到向量数据库
        Args:
            ids: 文档ID列表
            embeddings: 文档向量列表
            documents: 文档内容列表
            metadatas: 文档元数据列表
        """
        pass

    @abstractmethod
    async def add(
        self,
        id: str,
        embedding: List[float],
        document: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加单个文档到向量数据库
        Args:
            id: 文档ID
            embedding: 文档向量
            document: 文档内容
            metadata: 文档元数据
        """
        pass

    @abstractmethod
    async def update(
        self,
        id: str,
        embedding: Optional[List[float]] = None,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新文档
        Args:
            id: 文档ID
            embedding: 新的文档向量
            document: 新的文档内容
            metadata: 新的文档元数据
        """
        pass

    @abstractmethod
    async def delete(
        self,
        ids: Union[str, List[str]],
        filter: Optional[Dict[str, Any]] = None
    ) -> None:
        """删除文档
        Args:
            ids: 单个文档ID或ID列表
            filter: 基于元数据的过滤条件
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量
        Args:
            query_embedding: 查询向量
            limit: 返回结果数量
            filter: 基于元数据的过滤条件
        Returns:
            List[Dict]: 搜索结果列表，每个结果包含:
                - id: 文档ID
                - document: 文档内容
                - metadata: 文档元数据
                - score: 相似度分数
        """
        pass

    @abstractmethod
    async def get(
        self,
        ids: Optional[Union[str, List[str]]] = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取文档
        Args:
            ids: 单个文档ID或ID列表
            filter: 基于元数据的过滤条件
        Returns:
            List[Dict]: 文档列表，每个文档包含:
                - id: 文档ID
                - document: 文档内容
                - metadata: 文档元数据
                - embedding: 文档向量
        """
        pass

