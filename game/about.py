"""Credits of the About screen (WEB-08.2), shared by the web UI and Qt."""

from __future__ import annotations

from dataclasses import dataclass

SOURCE_URL = "https://github.com/dcs-retribution/dcs-retribution"

AUTHORS = (
    "DCS Retribution is an (independent) fork of DCS Liberation, which was "
    "originally developed by shdwp. DCS Liberation 2.0 is a partial rewrite based "
    "on this work by Khopa. DCS Retribution was forked during development of DCS "
    "Liberation v6.0.0 in 2022 by Raffson & MetalStormGhost."
)

CONTRIBUTORS = [
    "shdwp",
    "Khopa",
    "ColonelPanic",
    "RndName",
    "Roach",
    "Malakhit",
    "Wrycu",
    "calvinmorrow",
    "JohanAberg",
    "Deus",
    "SiKruger",
    "Mustang-25",
    "bgreman",
    "magwo",
    "SnappyComebacks",
    "kavinsky",
    "Schneefl0cke",
    "pbzweihander",
    "Raskil",
    "nosv1",
    "jake-lewis",
    "teamMOYA",
    "benedikt-wegmann",
    "movq",
    "bbirchnz",
    "eddiwood",
    "root0fall",
    "calvinmorrow",
    "UKayeF",
    "Captain Cody",
    "steveveepee",
    "pedromagueija",
    "parithon",
    "TheCandianVendingMachine",
    "bwRavencl",
    "davidp57",
    "Plob",
    "Hawkmoon",
    "alrik11es",
    "Starfire13",
    "Hornet2041/Lion",
    "SgtFuzzle17",
    "Doc_of_Mur",
    "NickJZX",
    "Sith1144",
    "Raffson",
    "MetalStormGhost",
    "HolyOrangeJuice (WRL)",
    "Adecarcer",
    "pande4360",
    "zhexu14",
    "ColonelAkirNakesh",
    "Nosajthedevil",
    "kivipe",
    "Turbolious",
    "ingax01",
    "M-Chimiste",
    "tmz42",
    "Drexyl",
    "Druss99",
    "Biggus22",
    "StillClock1",
]


@dataclass(frozen=True)
class Thanks:
    name: str
    reason: str


SPECIAL_THANKS = [
    Thanks("rp-", "for the pydcs framework"),
    Thanks("Grimes (mrSkortch) & Speed", "for the MIST framework"),
    Thanks("Ciribob", "for the JTACAutoLase.lua script"),
    Thanks("Walder", "for the Skynet-IADS script"),
    Thanks("Anubis Yinepu", "for the Hercules Cargo script"),
]


@dataclass(frozen=True)
class Attribution:
    text: str
    url: str


ATTRIBUTIONS = [
    Attribution(
        "Bug icons created by Freepik - Flaticon",
        "https://www.flaticon.com/free-icons/bug",
    ),
    Attribution(
        "Contains information from OpenStreetMap © OpenStreetMap contributors, "
        "made available under the Open Database License (ODbL)",
        "https://osmdata.openstreetmap.de/",
    ),
    Attribution(
        "Open Database License (ODbL)",
        "https://opendatacommons.org/licenses/odbl/1-0/",
    ),
    Attribution(
        "OpenStreetMap Data Extracts from Geofabrik",
        "https://download.geofabrik.de/index.html",
    ),
    Attribution("NASA EarthData", "https://www.earthdata.nasa.gov/"),
    Attribution(
        "Splash screen artwork by Andriy Dankovych (CC BY-SA)",
        "https://www.facebook.com/AndriyDankovych",
    ),
]
