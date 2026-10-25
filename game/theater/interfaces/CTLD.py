from typing import Optional, List, Tuple

from dcs import Point


class CTLD:
    ctld_zones: Optional[List[Tuple[Point, float]]] = None
    #: True when ctld_zones were generated (game.theater.ctldzones) rather than
    #: declared in the campaign. Class-level default keeps older saves loadable.
    ctld_zones_generated: bool = False
