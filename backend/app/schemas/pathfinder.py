from typing import Literal

from pydantic import BaseModel


class PathfinderRunRequest(BaseModel):
    direction: Literal["ingress", "egress", "both"] = "both"
