"""
BPMN Workflow Data Models
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class ElementType(str, Enum):
    """BPMN element types"""
    START_EVENT = "startEvent"
    END_EVENT = "endEvent"
    INTERMEDIATE_EVENT = "intermediateEvent"
    TIMER_INTERMEDIATE_CATCH_EVENT = "timerIntermediateCatchEvent"
    ERROR_BOUNDARY_EVENT = "errorBoundaryEvent"
    TIMER_BOUNDARY_EVENT = "timerBoundaryEvent"
    ESCALATION_BOUNDARY_EVENT = "escalationBoundaryEvent"
    SIGNAL_BOUNDARY_EVENT = "signalBoundaryEvent"
    TASK = "task"
    USER_TASK = "userTask"
    SERVICE_TASK = "serviceTask"
    SCRIPT_TASK = "scriptTask"
    SEND_TASK = "sendTask"
    RECEIVE_TASK = "receiveTask"
    MANUAL_TASK = "manualTask"
    BUSINESS_RULE_TASK = "businessRuleTask"
    AGENTIC_TASK = "agenticTask"
    SUB_PROCESS = "subProcess"
    CALL_ACTIVITY = "callActivity"
    EXCLUSIVE_GATEWAY = "exclusiveGateway"
    PARALLEL_GATEWAY = "parallelGateway"
    INCLUSIVE_GATEWAY = "inclusiveGateway"


class ConnectionType(str, Enum):
    """BPMN connection types"""
    SEQUENCE_FLOW = "sequenceFlow"
    MESSAGE_FLOW = "messageFlow"


class ExecutionStatus(str, Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class Lane(BaseModel):
    """Swimlane definition"""
    id: str
    name: str
    height: int


class Pool(BaseModel):
    """Pool (process participant) definition"""
    id: str
    name: str
    x: int
    y: int
    width: int
    height: int
    lanes: List[Lane] = []


class Element(BaseModel):
    """BPMN element definition"""
    id: str
    type: ElementType
    name: str
    x: int
    y: int
    poolId: Optional[str] = None
    laneId: Optional[str] = None
    attachedToRef: Optional[str] = None  # For boundary events - references parent task
    properties: Dict[str, Any] = Field(default_factory=dict)
    expanded: Optional[bool] = None
    width: Optional[int] = None
    height: Optional[int] = None
    childElements: Optional[List['Element']] = None
    childConnections: Optional[List['Connection']] = None

    def is_task(self) -> bool:
        """Check if element is a task type"""
        return self.type in [
            ElementType.TASK,
            ElementType.USER_TASK,
            ElementType.SERVICE_TASK,
            ElementType.SCRIPT_TASK,
            ElementType.SEND_TASK,
            ElementType.RECEIVE_TASK,
            ElementType.MANUAL_TASK,
            ElementType.BUSINESS_RULE_TASK,
            ElementType.AGENTIC_TASK,
            ElementType.SUB_PROCESS,
            ElementType.CALL_ACTIVITY
        ]

    def is_gateway(self) -> bool:
        """Check if element is a gateway"""
        return self.type in [
            ElementType.EXCLUSIVE_GATEWAY,
            ElementType.PARALLEL_GATEWAY,
            ElementType.INCLUSIVE_GATEWAY
        ]

    def is_event(self) -> bool:
        """Check if element is an event"""
        return self.type in [
            ElementType.START_EVENT,
            ElementType.END_EVENT,
            ElementType.INTERMEDIATE_EVENT
        ]


class Connection(BaseModel):
    """BPMN connection (flow) definition"""
    id: str
    type: ConnectionType = ConnectionType.SEQUENCE_FLOW
    name: Optional[str] = ""
    from_: str = Field(alias="from")
    to: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class Process(BaseModel):
    """BPMN process definition"""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    pools: List[Pool] = []
    elements: List[Element] = []
    connections: List[Connection] = []
    subprocess_definitions: List[Dict[str, Any]] = Field(default_factory=list, alias='subProcessDefinitions')


class Workflow(BaseModel):
    """Complete workflow definition"""
    process: Process

    def get_element_by_id(self, element_id: str) -> Optional[Element]:
        """Get element by ID"""
        for elem in self.process.elements:
            if elem.id == element_id:
                return elem
        return None

    def get_start_event(self) -> Optional[Element]:
        """Get the start event"""
        for elem in self.process.elements:
            if elem.type == ElementType.START_EVENT:
                return elem
        return None

    def get_outgoing_connections(self, element: Element) -> List[Connection]:
        """Get all outgoing connections from an element"""
        return [
            conn for conn in self.process.connections
            if conn.from_ == element.id
        ]

    def get_incoming_connections(self, element: Element) -> List[Connection]:
        """Get all incoming connections to an element"""
        return [
            conn for conn in self.process.connections
            if conn.to == element.id
        ]

    def get_outgoing_elements(self, element: Element) -> List[Element]:
        """Get all elements that follow this element"""
        outgoing_conns = self.get_outgoing_connections(element)
        elements = []
        for conn in outgoing_conns:
            target = self.get_element_by_id(conn.to)
            if target:
                elements.append(target)
        return elements


class TaskProgress(BaseModel):
    """Task execution progress"""
    status: str
    message: str
    progress: float  # 0.0 to 1.0
    result: Optional[Any] = None


class WorkflowInstance(BaseModel):
    """Runtime workflow instance"""
    instance_id: str
    workflow_id: str
    state: ExecutionStatus
    context: Dict[str, Any] = Field(default_factory=dict)
    current_element_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None


class ElementExecution(BaseModel):
    """Element execution record"""
    instance_id: str
    element_id: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class AGUIMessage(BaseModel):
    """AG-UI protocol message"""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    elementId: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class UserTaskInstance(BaseModel):
    """User task instance for human approval"""
    task_id: str
    task_name: str
    assignee: Optional[str] = None
    candidate_groups: List[str] = []
    priority: str = "Medium"
    due_date: Optional[str] = None
    form_fields: List[str] = []
    data: Dict[str, Any] = Field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.WAITING
    completion_data: Optional[Dict[str, Any]] = None
