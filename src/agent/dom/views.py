from dataclasses import dataclass,field
from textwrap import shorten
import json
from typing import Optional

@dataclass
class BoundingBox:
    left:int
    top:int
    width:int
    height:int

    def to_string(self):
        return f'({self.left},{self.top},{self.width},{self.height})'
    
    def to_dict(self):
        return {'left':self.left,'top':self.top,'width':self.width,'height':self.height}

@dataclass
class CenterCord:
    x:int
    y:int

    def to_string(self)->str:
        return f'({self.x},{self.y})'
    
    def to_dict(self):
        return {'x':self.x,'y':self.y}

@dataclass
class DOMNode:
    tag: str
    role: str
    element_type: str  # 'interactive', 'scrollable', 'informative'
    name: Optional[str] = None  # For interactive and scrollable
    content: Optional[str] = None  # For informative
    bounding_box: Optional[BoundingBox] = None  # For interactive
    center: Optional[CenterCord] = None  # For interactive and informative
    attributes: dict[str,str] = field(default_factory=dict)
    xpath: dict[str,str] = field(default_factory=dict)
    viewport: tuple[int,int] = field(default_factory=tuple)

    def __repr__(self):
        if self.element_type == 'interactive':
            return f"DOMNode(tag='{self.tag}', type='interactive', name='{self.name}', bbox={self.bounding_box}, xpath='{self.xpath}')"
        elif self.element_type == 'scrollable':
            return f"DOMNode(tag='{self.tag}', type='scrollable', name='{shorten(self.name or '',width=50)}', xpath='{self.xpath}')"
        else:
            content_preview = shorten(self.content or '', width=50)
            return f"DOMNode(tag='{self.tag}', type='informative', content='{content_preview}', xpath='{self.xpath}')"

    def to_dict(self) -> dict:
        result = {'tag': self.tag, 'role': self.role, 'type': self.element_type}
        if self.name:
            result['name'] = self.name
        if self.content:
            result['content'] = self.content
        if self.bounding_box:
            result['bounding_box'] = self.bounding_box.to_dict()
        if self.center:
            result['center'] = self.center.to_dict()
        if self.attributes:
            result['attributes'] = self.attributes
        return result

@dataclass
class TreeNodeData:
    tag: str
    role: str
    node_type: str  # 'interactive', 'informative', 'scrollable', 'structural'
    interactive_id: Optional[int] = None
    name: Optional[str] = None
    href: Optional[str] = None
    content: Optional[str] = None  # for informative nodes
    is_scrollable: bool = False

class TreeNode:
    def __init__(self, data: TreeNodeData):
        self.data = data
        self.children: list[TreeNode] = []

    def add_child(self, child: 'TreeNode') -> None:
        self.children.append(child)

@dataclass
class DOMState:
    interactive_nodes: list[DOMNode] = field(default_factory=list)
    informative_nodes: list[DOMNode] = field(default_factory=list)
    scrollable_nodes: list[DOMNode] = field(default_factory=list)
    selector_map: dict[str, DOMNode] = field(default_factory=dict)
    semantic_tree_root: Optional[TreeNode] = field(default=None)

    def __post_init__(self):
        if self.semantic_tree_root is None:
            self.semantic_tree_root = self._build_tree_from_xpaths()

    def _build_tree_from_xpaths(self) -> Optional[TreeNode]:
        if not self.interactive_nodes and not self.informative_nodes and not self.scrollable_nodes:
            return None

        root_data = TreeNodeData(tag='document', role='document', node_type='structural')
        root = TreeNode(root_data)
        xpath_to_node: dict[str, TreeNode] = {'': root}

        # Add interactive nodes
        for idx, node in enumerate(self.interactive_nodes):
            xpath = node.xpath.get('element', '')
            self._ensure_path_exists(root, xpath, xpath_to_node)

            data = TreeNodeData(
                tag=node.tag,
                role=node.role,
                node_type='interactive',
                interactive_id=idx,
                name=node.name,
                href=node.attributes.get('href')
            )
            node_obj = TreeNode(data)

            parts = [p for p in xpath.split('/') if p]
            if parts:
                parent_path = '/' + '/'.join(parts[:-1])
                if parent_path in xpath_to_node:
                    xpath_to_node[parent_path].add_child(node_obj)
            else:
                root.add_child(node_obj)

            xpath_to_node[xpath] = node_obj

        # Add scrollable nodes
        scrollable_xpaths = set()
        for idx, node in enumerate(self.scrollable_nodes):
            xpath = node.xpath.get('element', '')
            scrollable_xpaths.add(xpath)
            self._ensure_path_exists(root, xpath, xpath_to_node)

            data = TreeNodeData(
                tag=node.tag,
                role=node.role,
                node_type='scrollable',
                name=node.name,
                is_scrollable=True
            )
            node_obj = TreeNode(data)

            parts = [p for p in xpath.split('/') if p]
            if parts:
                parent_path = '/' + '/'.join(parts[:-1])
                if parent_path in xpath_to_node:
                    xpath_to_node[parent_path].add_child(node_obj)
            else:
                root.add_child(node_obj)

            xpath_to_node[xpath] = node_obj

        # Add informative nodes
        for node in self.informative_nodes:
            xpath = node.xpath.get('element', '')
            self._ensure_path_exists(root, xpath, xpath_to_node)

            data = TreeNodeData(
                tag=node.tag,
                role=node.role,
                node_type='informative',
                content=node.content
            )
            node_obj = TreeNode(data)

            parts = [p for p in xpath.split('/') if p]
            if parts:
                parent_path = '/' + '/'.join(parts[:-1])
                if parent_path in xpath_to_node:
                    xpath_to_node[parent_path].add_child(node_obj)
            else:
                root.add_child(node_obj)

            xpath_to_node[xpath] = node_obj

        return root

    def _ensure_path_exists(self, root: TreeNode, xpath: str, xpath_to_node: dict[str, TreeNode]) -> None:
        parts = [p for p in xpath.split('/') if p]
        current_path = ''
        current = root

        for part in parts[:-1]:
            current_path += '/' + part
            if current_path in xpath_to_node:
                current = xpath_to_node[current_path]
            else:
                tag = part.rsplit('[', 1)[0] if '[' in part else part
                data = TreeNodeData(tag=tag, role=tag, node_type='structural')
                node = TreeNode(data)
                current.add_child(node)
                xpath_to_node[current_path] = node
                current = node

    def semantic_tree_to_string(self) -> str:
        if not self.semantic_tree_root:
            return 'No elements'

        lines: list[str] = []
        self._render_tree(self.semantic_tree_root, lines, '', is_last=True)
        return '\n'.join(lines)

    def _render_tree(self, node: TreeNode, lines: list[str], prefix: str, is_last: bool) -> None:
        if node.data.tag == 'document':
            lines.append(f"{node.data.tag}  [role: {node.data.role}]")
        else:
            connector = '└── ' if is_last else '├── '
            line = self._format_node(node)
            lines.append(f"{prefix}{connector}{line}")

        extension = '    ' if is_last else '│   '
        new_prefix = prefix + extension

        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            self._render_tree(child, lines, new_prefix, is_last_child)

    def _format_node(self, node: TreeNode) -> str:
        if node.data.node_type == 'interactive':
            label = f"[#{node.data.interactive_id}]"
            if node.data.href:
                return f"{label} {node.data.tag} \"{node.data.name}\"  → {node.data.href}"
            else:
                return f"{label} {node.data.tag} \"{node.data.name}\""
        elif node.data.node_type == 'scrollable':
            return f"{node.data.tag}  [scrollable] \"{node.data.name}\""
        elif node.data.node_type == 'informative':
            content_preview = shorten(node.data.content or '', width=50)
            return f"{node.data.tag}  \"{content_preview}\""
        else:
            return f"{node.data.tag}  [role: {node.data.role}]"

    def interactive_elements_to_string(self)->str:
        if not self.interactive_nodes:
            return 'No interactive elements'
        header = '# id|tag|role|name|coords|attributes'
        rows = [header]
        for index, node in enumerate(self.interactive_nodes):
            row = f'{index}|{node.tag}|{node.role}|{node.name}|{node.center.to_string()}|{json.dumps(node.attributes)}'
            rows.append(row)
        return '\n'.join(rows)

    def informative_elements_to_string(self)->str:
        return  '\n'.join([f'Tag: {node.tag} Role: {node.role} Content: {node.content}' for node in self.informative_nodes])

    def scrollable_elements_to_string(self)->str:
        if not self.scrollable_nodes:
            return 'No scrollable elements'
        header = '# id|tag|role|name|attributes'
        rows = [header]
        base_index = len(self.interactive_nodes)
        for index, node in enumerate(self.scrollable_nodes):
            row = f'{base_index + index}|{node.tag}|{node.role}|{shorten(node.name, width=500)}|{json.dumps(node.attributes)}'
            rows.append(row)
        return '\n'.join(rows)
    
