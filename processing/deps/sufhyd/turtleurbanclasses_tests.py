#!/usr/bin/python
# -*- coding: utf-8 -*-
# ***********************************************************************
#
# This file is part of the nens library.
#
# the nens library is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# the nens library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the nens libraray.  If not, see
# <http://www.gnu.org/licenses/>.
#
# Copyright 2011 Nelen & Schuurmans
# original part of the 'nens' library
# ***********************************************************************
# *
# * Project    : various
# *
# * $Id$
# *
# * initial programmer :  Mario Frasca
# * initial date       :  2008-07-28
# **********************************************************************

from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import AfvoerendOppervlak
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import AfvoerendOppervlak_Knoop
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import AfvoerendOppervlak_Tak
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import AlgemeneInformatie
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import BergendOppervlakKnoop
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Doorlaat
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import DWALozingMetDagcyclus
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import DWAVerloopPerInwoner
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import End
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Gemaal
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Gemaal_Knoop
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Gemaal_Tak
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import GeslotenLeiding
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import GmlElement
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import HydroObjectFactory
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import InitieleLeidingWaarden
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import isSufHydKey
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Knoop
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Overstort
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Overstort_Knoop
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import Overstort_Tak
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import UitlaatMetKeerklep
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import UitlaatMetKeerklep_Knoop
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import UitlaatMetKeerklep_Tak

import logging
import mock
import re
import unittest


handler = mock.Handler(level=logging.DEBUG)

# 2019-04-18 Reinout: disabled this handler as it spams the log when
# running pytest with --flake8. TODO: is this test file actually needed?
# logging.getLogger("").addHandler(handler)
# TODO: replace with pytest log fixture


class MockWriter:
    laws = [
        ("gml:boundedBy", "geometry", True),
        ('<?xml version="1.0" encoding="UTF-8"?>', "header", True),
        ("<schema ", "schema", (None, False)),
        ("</schema>", "schema", (False, True)),
        ('<complexType name="End">', "end-decl", True),
        ("<fme:End ", "end-def", True),
        ("</gml:FeatureCollection>", "trailer", True),
    ]

    def __init__(self):
        # pattern, key, value/{value_n -> value_{n+1}}
        self.got = dict([(k, None) for _, k, _ in self.laws])
        self.buffer = []

    def write(self, s):
        if isinstance(s, str):
            self.buffer.append(s)
            for pattern, key, value in self.laws:
                if s.find(pattern) != -1:
                    if value:
                        self.got[key] = True
                    else:
                        expected, next = value
                        if expected == self.got.get(key, None):
                            self.got[key] = next


sampleStrings = {
    "SUFHYD": {
        Knoop: [
            "*KNP   0000NOORD1                 164371100  388463700   19.14  0   100   100.000        00    5.00                   ",
            "*KNP   0000NOORD2                 163804600  385965500   19.14  0   100   100.000        00    2.00                   ",
            "*KNP   000RWZINRD                 162964800  385605500   15.41  0   100     1.000        00    8.00                   ",
            "*KNP   0000NUENEN                 166060600  386760700   19.14  0   100    36.742        00    6.14                   ",
            "*KNP   000NUENEN2                 166065600  386760700   19.14  0   100     4.000        00    6.14                   ",
            "*KNP   0000000SON                 161906300  391141200   19.14  0   100    33.387        00    6.14                   ",
            "*KNP   000000SON2                 161911300  391141200   19.14  0   100     4.000        00    6.14                   ",
            "*KNP   0000H1280A                 162962100  385564800   15.80  0   100     2.700        00    0.95                   ",
            "*KNP   00RWZISTAD                 162964800  385603500   15.25  0   100     1.000        00    8.00                   ",
            "*KNP   0000H1281A                 162967500  385642200   14.51  0   100     2.100        00    0.84                   ",
            "*KNP   0000J0650W                 163398000  388522000   15.20  0   100     2.200        00   12.38                   ",
            "*KNP   0000C0950A                 157059000  387120000   17.93 00   100 00  0.700  0.700 00   16.38     0     0     0    2.03   0    ",
            "*KNP   000BYPASS1                 162904500  385605500   15.00  0   200     7.000        00    1.00                   ",
            "*KNP   000BYPASS2                 162887700  385605500   13.00  0   200     7.000        00    0.45                   ",
            "*KNP   00REGENTNK                 162921300  385607500   19.00  0   200    38.730        00    2.05                   ",
            "*KNP   00000MEERN                 158363200  379653500   25.00  0   100   160.000        00    4.21                   ",
            "*KNP   00000AALST                 160847900  379683300   25.00  0   100   160.000        00    2.60                   ",
            "*KNP   00000GLDRP                 166975000  382593400   25.00  0   100    46.340        00    6.14                   ",
            "*KNP   0000GLDRP2                 166980000  382593400   25.00  0   100     4.000        00    6.14                   ",
            "*KNP   0000K16620                 164047100  383583200   18.15  0   100     0.316        00   16.05                   ",
            "*KNP   0000K16618                 164014400  383590700   18.15  0   100     0.600        00   16.00                   ",
            "*KNP    000 GLDRP                 164014500  383594700   18.15  0   100     0.600        00   16.00                   ",
            "*KNP   000 GLDRP2                 164014600  383593700   18.15  0   100     0.600        00   16.00                   ",
            "*KNP 0001002                      164014700  383592700   18.15  0   100     0.600        00   16.00                   ",
            "*KNP 0001001                      164014800  383591700   18.15  0   100     0.600        00   16.00                   ",
        ],
        GeslotenLeiding: [
            "*LEI   0000NOORD1   0000NOORD2      5.00    2.002561.63           1.500  2.000 02                                      ",
            "*LEI   0000NOORD2   000RWZINRD      2.00    1.00 999.00           1.500  2.000 02                                      ",
            "*LEI   0000NUENEN   000NUENEN2      6.14    6.14  50.00           1.000        04                                      ",
            "*LEI   0000000SON   000000SON2      6.14    6.14  50.00           1.000        04                                      ",
            "*LEI   0000H1280A   00RWZISTAD      0.95    0.00  38.79           1.500  1.000 02                                      ",
            "*LEI   0000H1281A   00RWZISTAD      0.84    0.00  38.80           1.500  1.000 02                                      ",
            "*LEI   000BYPASS1   000BYPASS2      1.00    0.45  29.95           3.500  2.500 02                                      ",
            "*LEI   00REGENTNK   000BYPASS1      2.05    1.05  29.82           3.500  2.500 02                                      ",
            "*LEI   00000MEERN   00000AALST      4.21    2.602484.88           1.900  1.500 02                                      ",
            "*LEI   00000GLDRP   0000GLDRP2      6.14    6.14  50.00           1.000        04                                      ",
            "*LEI   0000K16618   0000K16620     16.00   16.05  33.49           0.400  0.600 01           0.00                         8  ",
            "*LEI 0001001      0001002      1   -2.41   -2.42  39.10 99 99     0.300  0.300 99    00        0        0        0   0          000.000.000.000.00           ",
            "*LEI   000 GLDRP2    000 GLDRP      6.14    6.14  50.00           1.000        04                                      ",
        ],
        Gemaal: [
            "*GEM   0000B1436F   0000C1677D 0             1   50.00   15.40   14.90           ",
            "*GEM   0000F1684P                            2   33.33   14.26   13.91                   66.67   14.36   13.92                ",
            "*GEM   00000AALST   0000GEMAAL 0             2  625.83   12.66   12.61                 3000.00   12.96   12.66                ",
            "*GEM   0000B15756   0000C16006 0             1   50.00   15.40   14.90           ",
            "*GEM   00000AALST   0000GEMAAL 0             2  625.83   12.66   12.61                 3000.00   12.96   12.66                 3000.00   12.96   12.66",
            "*GEM   00000AALST   0000GEMAAL 0             3  625.83   12.66   12.61                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66",
            "*GEM   00000AALST   0000GEMAAL 0             4  625.83   12.66   12.61                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66",
            "*GEM   00000AALST   0000GEMAAL 0             5  625.83   12.66   12.61                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66",
            "*GEM   00000AALST   0000GEMAAL 0             6  625.83   12.66   12.61                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66",
            "*GEM   00000AALST   0000GEMAAL 0             7  625.83   12.66   12.61                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66                 3000.00   12.96   12.66",
        ],
        AlgemeneInformatie: [
            r"*AL1 1.10  20050315",
            r"*AL2",
            r"*AL3",
            r"*AL4 dwa                                                                   ",
            r"*AL5 exported from Sobek D:\Sobek\EHOVEN.lit\3                             ",
        ],
        DWALozingMetDagcyclus: [
            "*LZD   0000D19756                                        31.94  0.0  0.0  0.0  0.0  0.0  0.0  0.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  1.0  0.0  0.0  0.0"
        ],
        DWAVerloopPerInwoner: [
            "*DWA             1.5  1.5  1.5  1.5  1.5  3.0  4.0  5.0  6.0  6.5  7.5  8.5  7.5  6.5  6.0  5.0  5.0  5.0  4.0  3.5  3.0  2.5  2.0  2.0",
            "*DWA 2.50 12.00  2.1  1.6  2.0  1.6  1.5  3.0  6.5  6.3  4.2  5.2  4.3  5.1  5.4  4.8  6.3  5.4  5.0  5.1  4.6  3.4  3.7  4.1  5.1  3.7   2    104.00                                         3 ",
        ],
        AfvoerendOppervlak: [
            "*AFV   0000NUENEN                       0.00500000.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   0000NUENEN   000NUENEN2          0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   0000000SON                       0.00238571.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   0000000SON   000000SON2          0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   00000GLDRP                       3.00857140.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   00000GLDRP   0000GLDRP2          0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   00000GYZEN                       1.00585710.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   00000GYZEN   0000GYZEN2          0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   00000HEEZE                       9.00600000.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   00000HEEZE   0000HEEZE2          0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00        0.00     0.00     0.00",
            "*AFV   0000B07752   0000C07002                6783.0",
            "*AFV   0000B07754   0000B07756                1488.0",
            "*AFV   0000B07754   0000B0775U                923.0",
            "*AFV   0000G09364   0000G09366                1241.0",
            "*AFV   0000G09390   0000G09392                349.0",
            "*AFV   0000G09306   0000G09308                862.0",
            "*AFV   0000G09334   0000G09336                754.0",
        ],
        Overstort: [
            "*OVS   000000SON2                10.000   17.14 0.941   1   17.04",
            "*OVS   000000VBT1   000BYPASS1 0  4.500   14.00 0.941   1                                                               ",
            "*OVS   000000VBT2   000BYPASS1 0  4.500   14.00 0.941   1        ",
            "*OVS   000000VBT3   000BYPASS1 0  4.500   14.00 0.941   1        ",
            "*OVS   0000A1328U       B1300W    3.200   17.44 0.941                    ",
            "*OVS   0000A1402U       A1402W    0.500   18.40 0.941                   ",
            "*OVS   0000A1402U       A1403W    0.500   18.40 0.941                   ",
            "*OVS   0000A1402W                 2.000   19.55 0.941   1   18.20",
            "*OVS   0000A1403W                 2.000   19.55 0.941   1   18.20",
            "*OVS   0000B0775U       B0775W    3.200   16.23 0.941                   ",
            "*OVS   000000SON2 0              10.000   17.14 0.941   1   17.04",
        ],
        UitlaatMetKeerklep: [
            "*UIT tm00051R0308                          -4.80   -4.80",
            "*UIT   000000VBT1   000BYPASS1 0   -4.80                ",
            "*UIT tm00053R0172                       ****************",
            "*UIT tm00053R0093                  -4.80                ",
        ],
        Doorlaat: [
            "*DRL   0000E2100U   0000E2100W 0  3.000  0.300 02   16.55 0.600          0",
            "*DRL   0000E2230U   0000E2275W 0  3.000  0.870 02   16.13 0.600          0",
            "*DRL   0000G2175U   0000G2175W 0  3.300  0.850 02   16.02 0.600          0",
            "*DRL   0000F2075U   0000F2080W 0  3.000  0.410 02   15.64 0.600          0",
            "*DRL   0000G1679U   0000G1681W 0  3.300  0.190 02   14.86 0.600          0",
            "*DRL   0000G1680U   0000G1680W 0  3.000  0.240 02   14.86 0.600          0",
        ],
        BergendOppervlakKnoop: [
            "*BOP 00   0303338                   210000.00    0.8    0.40    0.8"
        ],
        InitieleLeidingWaarden: ["*INI  0   55R0323  0   55R0324 1  0.0000 1   -5.15"],
        End: ["*END"],
    },
    "GML": {
        Knoop: [
            '<gml:featureMember>\n<fme:Knoop gml:id="id%(gml__id)s">\n<fme:fid>0</fme:fid>\n<fme:objectid>0</fme:objectid>\n<fme:opmerking></fme:opmerking>\n<fme:ide_rec>*KNP</fme:ide_rec>\n<fme:ide_geb></fme:ide_geb>\n<fme:ide_knp>0000NOORD1</fme:ide_knp>\n<fme:knp_xco>164371.100</fme:knp_xco>\n<fme:knp_yco>388463.700</fme:knp_yco>\n<fme:mvd_niv>19.14</fme:mvd_niv>\n<fme:mvd_sch>0</fme:mvd_sch>\n<fme:wos_opp>100</fme:wos_opp>\n<fme:pro_mat></fme:pro_mat>\n<fme:knp_bre>100.000</fme:knp_bre>\n<fme:knp_len></fme:knp_len>\n<fme:knp_vrm>00</fme:knp_vrm>\n<fme:knp_bok>5.00</fme:knp_bok>\n<fme:afv_hel></fme:afv_hel>\n<fme:afv_vla></fme:afv_vla>\n<fme:afv_vlu></fme:afv_vlu>\n<fme:loz_con></fme:loz_con>\n<fme:aan_won></fme:aan_won>\n<fme:aan_inw></fme:aan_inw>\n<fme:dwa_def></fme:dwa_def>\n<gml:pointProperty>\n<gml:Point srsName="EPSG:28992" srsDimension="2">\n<gml:pos>164371.100 388463.700</gml:pos>\n</gml:Point>\n</gml:pointProperty>\n</fme:Knoop>\n</gml:featureMember>',
            """\
<gml:featureMember>
<fme:RWA_knopenAM_inclFouteDWAKnp gml:id="id8c2bbbd3-ba17-433f-b3e3-af10aa16b6a6">
<fme:FID>0</fme:FID>
<fme:OBJECTID>105</fme:OBJECTID>
<fme:IDE_REC>*KNP</fme:IDE_REC>
<fme:IDE_GEB>0</fme:IDE_GEB>
<fme:IDE_KNP>25R0625</fme:IDE_KNP>
<fme:KNP_XCO>144068.42</fme:KNP_XCO>
<fme:KNP_YCO>487283.7</fme:KNP_YCO>
<fme:MVD_NIV>-3.56</fme:MVD_NIV>
<fme:MVD_SCH> </fme:MVD_SCH>
<fme:WOS_OPP>0</fme:WOS_OPP>
<fme:PRO_MAT> </fme:PRO_MAT>
<fme:KNP_BRE>0.8</fme:KNP_BRE>
<fme:KNP_LEN>0.8</fme:KNP_LEN>
<fme:KNP_VRM> </fme:KNP_VRM>
<fme:KNP_BOK>0</fme:KNP_BOK>
<fme:AFV_HEL>0</fme:AFV_HEL>
<fme:AFV_VLA>0</fme:AFV_VLA>
<fme:AFV_VLU>0</fme:AFV_VLU>
<fme:LOZ_CON>0</fme:LOZ_CON>
<fme:AAN_WON>0</fme:AAN_WON>
<fme:AAN_INW>0</fme:AAN_INW>
<fme:GRONDDEKKI>0</fme:GRONDDEKKI>
<fme:GEBIED>0</fme:GEBIED>
<fme:Opm> </fme:Opm>
<fme:Plangebied> </fme:Plangebied>
<fme:ID_geb_ori>2</fme:ID_geb_ori>
<fme:Type>RWA</fme:Type>
<fme:ET_ID>10</fme:ET_ID>
<fme:ET_Source>L:\Extern\projecten H (2006)\H0106 - Herberekening rioolstelsel Almere\GIS\Features\Stappen\9 Almere Midden\RWAstelsel\RWA-Knopen.shp</fme:ET_Source>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>144068 487284</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:RWA_knopenAM_inclFouteDWAKnp>
</gml:featureMember>
""",
            """\
<gml:featureMember>
<fme:Knoop gml:id="id%(gml__id)s">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:opmerking></fme:opmerking>
<fme:ide_rec>*KNP</fme:ide_rec>
<fme:ide_geb></fme:ide_geb>
<fme:ide_knp>0000NOORD1</fme:ide_knp>
<fme:knp_xco>164371.100</fme:knp_xco>
<fme:knp_yco>388463.700</fme:knp_yco>
<fme:mvd_niv>19.14</fme:mvd_niv>
<fme:mvd_sch>0</fme:mvd_sch>
<fme:wos_opp>100</fme:wos_opp>
<fme:pro_mat></fme:pro_mat>
<fme:knp_bre>100.000</fme:knp_bre>
<fme:knp_len></fme:knp_len>
<fme:knp_vrm>00</fme:knp_vrm>
<fme:knp_bok>5.00</fme:knp_bok>
<fme:afv_hel></fme:afv_hel>
<fme:afv_vla></fme:afv_vla>
<fme:afv_vlu></fme:afv_vlu>
<fme:loz_con></fme:loz_con>
<fme:aan_won></fme:aan_won>
<fme:aan_inw></fme:aan_inw>
<fme:dwa_def></fme:dwa_def>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>164371.100 388463.700</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:Knoop>
</gml:featureMember>""",
            """\
<gml:featureMember>
<fme:Knoop_point gml:id="id371edd68-94b6-40c2-913a-23feb36009ee">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*KNP</fme:ide_rec>
<fme:ide_knp>00000DWA_2</fme:ide_knp>
<fme:knp_xco>140031.2</fme:knp_xco>
<fme:knp_yco>490003</fme:knp_yco>
<fme:mvd_niv>-3.3</fme:mvd_niv>
<fme:mvd_sch>0</fme:mvd_sch>
<fme:wos_opp>125</fme:wos_opp>
<fme:knp_bre>0.8</fme:knp_bre>
<fme:knp_vrm>00</fme:knp_vrm>
<fme:knp_bok>-5.97</fme:knp_bok>
<fme:aan_inw>0</fme:aan_inw>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>87</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140031.199999999 490003</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:Knoop_point>
</gml:featureMember>
""",
        ],
        GeslotenLeiding: [
            '<gml:featureMember>\n<fme:GeslotenLeiding gml:id="id%(gml__id)s">\n<fme:fid>0</fme:fid>\n<fme:objectid>0</fme:objectid>\n<fme:opmerking></fme:opmerking>\n<fme:ide_rec>*LEI</fme:ide_rec>\n<fme:ide_geb></fme:ide_geb>\n<fme:ide_kn1>0000NOORD1</fme:ide_kn1>\n<fme:ide_gb2></fme:ide_gb2>\n<fme:ide_kn2>0000NOORD2</fme:ide_kn2>\n<fme:num_mvb></fme:num_mvb>\n<fme:bob_kn1>5.00</fme:bob_kn1>\n<fme:bob_kn2>2.00</fme:bob_kn2>\n<fme:lei_len>2561.63</fme:lei_len>\n<fme:lei_typ></fme:lei_typ>\n<fme:pro_mat></fme:pro_mat>\n<fme:mat_sdr></fme:mat_sdr>\n<fme:pro_bre>1.500</fme:pro_bre>\n<fme:pro_hgt>2.000</fme:pro_hgt>\n<fme:pro_vrm>02</fme:pro_vrm>\n<fme:pro_num></fme:pro_num>\n<fme:afv_een></fme:afv_een>\n<fme:afv_hel></fme:afv_hel>\n<fme:afv_vla></fme:afv_vla>\n<fme:afv_vlu></fme:afv_vlu>\n<fme:aan_won></fme:aan_won>\n<fme:aan_inw></fme:aan_inw>\n<fme:pro_knw></fme:pro_knw>\n<fme:str_rch></fme:str_rch>\n<fme:inv_kn1></fme:inv_kn1>\n<fme:uit_kn1></fme:uit_kn1>\n<fme:inv_kn2></fme:inv_kn2>\n<fme:uit_kn2></fme:uit_kn2>\n<fme:qdh_num></fme:qdh_num>\n<fme:qdh_niv></fme:qdh_niv>\n<fme:nsh_frt></fme:nsh_frt>\n<fme:nsh_frv></fme:nsh_frv>\n<fme:dwa_def></fme:dwa_def>\n<fme:nsh_upt></fme:nsh_upt>\n<fme:nsh_upn></fme:nsh_upn>\n<gml:curveProperty>\n<gml:LineString srsName="EPSG:28992" srsDimension="2">\n<gml:posList>0.000 0.000 0.000 0.000</gml:posList>\n</gml:LineString>\n</gml:curveProperty>\n</fme:GeslotenLeiding>\n</gml:featureMember>',
            """\
<gml:featureMember>
<fme:GeslotenLeiding gml:id="id%(gml__id)s">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:opmerking></fme:opmerking>
<fme:ide_rec>*LEI</fme:ide_rec>
<fme:ide_geb></fme:ide_geb>
<fme:ide_kn1>0000K16618</fme:ide_kn1>
<fme:ide_gb2></fme:ide_gb2>
<fme:ide_kn2>0000K16620</fme:ide_kn2>
<fme:num_mvb></fme:num_mvb>
<fme:bob_kn1>16.00</fme:bob_kn1>
<fme:bob_kn2>16.05</fme:bob_kn2>
<fme:lei_len>33.49</fme:lei_len>
<fme:lei_typ></fme:lei_typ>
<fme:pro_mat></fme:pro_mat>
<fme:mat_sdr></fme:mat_sdr>
<fme:pro_bre>0.400</fme:pro_bre>
<fme:pro_hgt>0.600</fme:pro_hgt>
<fme:pro_vrm>01</fme:pro_vrm>
<fme:pro_num></fme:pro_num>
<fme:afv_een></fme:afv_een>
<fme:afv_hel>0.00</fme:afv_hel>
<fme:afv_vla></fme:afv_vla>
<fme:afv_vlu></fme:afv_vlu>
<fme:aan_won></fme:aan_won>
<fme:aan_inw>8</fme:aan_inw>
<fme:pro_knw></fme:pro_knw>
<fme:str_rch></fme:str_rch>
<fme:inv_kn1></fme:inv_kn1>
<fme:uit_kn1></fme:uit_kn1>
<fme:inv_kn2></fme:inv_kn2>
<fme:uit_kn2></fme:uit_kn2>
<fme:qdh_num></fme:qdh_num>
<fme:qdh_niv></fme:qdh_niv>
<gml:curveProperty>
<gml:LineString srsName="EPSG:28992" srsDimension="2">
<gml:posList>0.000 0.000 0.000 0.000</gml:posList>
</gml:LineString>
</gml:curveProperty>
</fme:GeslotenLeiding>
</gml:featureMember>""",
            """\
<gml:featureMember>
<fme:RWA_leidingenAM_inclFouteDWALei gml:id="id7ceda715-59d5-4448-bef5-b289cf590160">
<fme:FID>0</fme:FID>
<fme:OBJECTID>14178</fme:OBJECTID>
<fme:IDE_REC>*LEI</fme:IDE_REC>
<fme:IDE_GEB>0</fme:IDE_GEB>
<fme:IDE_KN1>24R0815</fme:IDE_KN1>
<fme:IDE_KN2>24R0816</fme:IDE_KN2>
<fme:NUM_MVB>0</fme:NUM_MVB>
<fme:BOB_KN1>-5.75</fme:BOB_KN1>
<fme:BOB_KN2>-5.75</fme:BOB_KN2>
<fme:LEI_LEN>60</fme:LEI_LEN>
<fme:LEI_TYP>RW</fme:LEI_TYP>
<fme:PRO_MAT>P34</fme:PRO_MAT>
<fme:MAT_SDR>0</fme:MAT_SDR>
<fme:PRO_BRE>0.25</fme:PRO_BRE>
<fme:PRO_HGT>0</fme:PRO_HGT>
<fme:PRO_VRM>00</fme:PRO_VRM>
<fme:PRO_NUM> </fme:PRO_NUM>
<fme:AFV_EEN> </fme:AFV_EEN>
<fme:AFV_HEL>0</fme:AFV_HEL>
<fme:AFV_VLA>2012.0046</fme:AFV_VLA>
<fme:AFV_VLU>0</fme:AFV_VLU>
<fme:AAN_WON>0</fme:AAN_WON>
<fme:AAN_INW>0</fme:AAN_INW>
<fme:PRO_KNW>0</fme:PRO_KNW>
<fme:STR_RCH> </fme:STR_RCH>
<fme:INV_KN1>0</fme:INV_KN1>
<fme:UIT_KN1>0</fme:UIT_KN1>
<fme:INV_KN2>0</fme:INV_KN2>
<fme:UIT_KN2>0</fme:UIT_KN2>
<fme:QDH_NUM> </fme:QDH_NUM>
<fme:QDH_NIV>0</fme:QDH_NIV>
<fme:LENGTE_HEM>0</fme:LENGTE_HEM>
<fme:STROOKBREE>0</fme:STROOKBREE>
<fme:VERHANG>0</fme:VERHANG>
<fme:GEBIED>0</fme:GEBIED>
<fme:IDE_LEI> </fme:IDE_LEI>
<fme:LEI_XCO1>144162.736</fme:LEI_XCO1>
<fme:LEI_YCO1>485310.304</fme:LEI_YCO1>
<fme:LEI_XCO2>144134.985</fme:LEI_XCO2>
<fme:LEI_YCO2>485363.85</fme:LEI_YCO2>
<fme:Shape_Leng>0</fme:Shape_Leng>
<fme:Opmerking_> </fme:Opmerking_>
<fme:Opm_BOBkn2> </fme:Opm_BOBkn2>
<fme:GEM_BOB>-5.75</fme:GEM_BOB>
<fme:Opm_Type_L> </fme:Opm_Type_L>
<fme:Plangebied> </fme:Plangebied>
<fme:ID_geb_ori> </fme:ID_geb_ori>
<fme:Opm_breedt> </fme:Opm_breedt>
<fme:Opm_bron> </fme:Opm_bron>
<fme:LeidingID_>24R0815_24R0816</fme:LeidingID_>
<fme:check_vers>0</fme:check_vers>
<fme:ET_ID>44</fme:ET_ID>
<fme:ET_Source>L:\Extern\projecten H (2006)\H0106 - Herberekening rioolstelsel Almere\GIS\Features\Stappen\9 Almere Midden\RWAstelsel\FoutDWA_leidingenAM.shp</fme:ET_Source>
<gml:curveProperty>
<gml:LineString srsName="EPSG:28992" srsDimension="2">
<gml:posList>144163 485310 144135 485364</gml:posList>
</gml:LineString>
</gml:curveProperty>
</fme:RWA_leidingenAM_inclFouteDWALei>
</gml:featureMember>
""",
        ],
        AfvoerendOppervlak: [
            """\
<gml:featureMember>
<fme:AfvoerendOppervlak_Knoop_point gml:id="id5efcfc05-24e8-4d8a-9cd0-51d6b180907d">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*AFV</fme:ide_rec>
<fme:ide_kn1>00000RWA_3</fme:ide_kn1>
<fme:gvh_hel>0</fme:gvh_hel>
<fme:gvh_vla>0</fme:gvh_vla>
<fme:gvh_vlu>0</fme:gvh_vlu>
<fme:ovh_hel>0</fme:ovh_hel>
<fme:ovh_vla>0</fme:ovh_vla>
<fme:ovh_vlu>0</fme:ovh_vlu>
<fme:dak_hel>0</fme:dak_hel>
<fme:dak_vla>0</fme:dak_vla>
<fme:dak_vlu>0</fme:dak_vlu>
<fme:onv_hel>0</fme:onv_hel>
<fme:onv_vla>0</fme:onv_vla>
<fme:onv_vlu>0</fme:onv_vlu>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>1</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140613.899999999 490214.399999999</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:AfvoerendOppervlak_Knoop_point>
</gml:featureMember>
""",
            """\
<gml:featureMember>
<fme:AfvoerendOppervlak_Tak_line gml:id="id8d8fcd72-9afe-490b-97c4-abcc694bf419">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*AFV</fme:ide_rec>
<fme:ide_kn1>0000DWA_55</fme:ide_kn1>
<fme:ide_kn2>0000DWA_56</fme:ide_kn2>
<fme:gvh_hel>0</fme:gvh_hel>
<fme:gvh_vla>0</fme:gvh_vla>
<fme:gvh_vlu>0</fme:gvh_vlu>
<fme:ovh_hel>0</fme:ovh_hel>
<fme:ovh_vla>0</fme:ovh_vla>
<fme:ovh_vlu>0</fme:ovh_vlu>
<fme:dak_hel>0</fme:dak_hel>
<fme:dak_vla>0</fme:dak_vla>
<fme:dak_vlu>0</fme:dak_vlu>
<fme:onv_hel>0</fme:onv_hel>
<fme:onv_vla>0</fme:onv_vla>
<fme:onv_vlu>0</fme:onv_vlu>
<fme:gml_geometry_property>curveProperty</fme:gml_geometry_property>
<fme:Object_ID>132</fme:Object_ID>
<fme:Shape_Length>76.9532325506379</fme:Shape_Length>
<gml:curveProperty>
<gml:LineString srsName="EPSG:28992" srsDimension="2">
<gml:posList>140301.5 490253.199999999 140233.699999999 490216.800000001</gml:posList>
</gml:LineString>
</gml:curveProperty>
</fme:AfvoerendOppervlak_Tak_line>
</gml:featureMember>
""",
        ],
        Gemaal: [
            """\
<gml:featureMember>
<fme:Gemaal_Knoop_point gml:id="id8b7201db-45cb-4377-ade1-303af78745a7">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*GEM</fme:ide_rec>
<fme:ide_kn1>0000Gemaal</fme:ide_kn1>
<fme:pmp_com>1</fme:pmp_com>
<fme:pmp_pc1>3.06</fme:pmp_pc1>
<fme:pmp_an1>-6.78</fme:pmp_an1>
<fme:pmp_af1>-6.99</fme:pmp_af1>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>1</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140181.5 490091.600000001</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:Gemaal_Knoop_point>
</gml:featureMember>
""",
            """\
<gml:featureMember>
<fme:Gemaal_Tak_line gml:id="id4df303aa-7618-4fa0-bb57-83c523f0d5cc">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*GEM</fme:ide_rec>
<fme:ide_kn1>0000DWA_76</fme:ide_kn1>
<fme:ide_kn2>0000DWA_72</fme:ide_kn2>
<fme:num_mvb>0</fme:num_mvb>
<fme:pmp_com>1</fme:pmp_com>
<fme:pmp_pc1>0.19</fme:pmp_pc1>
<fme:pmp_an1>-5.35</fme:pmp_an1>
<fme:pmp_af1>-5.5</fme:pmp_af1>
<fme:gml_geometry_property>curveProperty</fme:gml_geometry_property>
<fme:Object_ID>1</fme:Object_ID>
<fme:Shape_Length>39.0749280266559</fme:Shape_Length>
<gml:curveProperty>
<gml:LineString srsName="EPSG:28992" srsDimension="2">
<gml:posList>140482.100000001 490362.100000001 140447.899999999 490343.199999999</gml:posList>
</gml:LineString>
</gml:curveProperty>
</fme:Gemaal_Tak_line>
</gml:featureMember>
""",
        ],
        Overstort: [
            """\
<gml:featureMember>
<fme:Overstort_Knoop_point gml:id="idaacef2b1-5a53-49ce-ad05-df29e5fd7458">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*OVS</fme:ide_rec>
<fme:ide_kn1>0000Weir_4</fme:ide_kn1>
<fme:ovs_bre>1</fme:ovs_bre>
<fme:ovs_niv>-5.45</fme:ovs_niv>
<fme:ovs_coe>0.8</fme:ovs_coe>
<fme:str_rch>0</fme:str_rch>
<fme:bws_gem>-5.2</fme:bws_gem>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>1</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140215.300000001 490050.800000001</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:Overstort_Knoop_point>
</gml:featureMember>
<gml:featureMember>
""",
            """\
<fme:Overstort_Knoop_point gml:id="id8fdd1163-1939-4da5-a0d0-2ae5e2040ae8">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*OVS</fme:ide_rec>
<fme:ide_kn1>0000Weir_3</fme:ide_kn1>
<fme:ovs_bre>1</fme:ovs_bre>
<fme:ovs_niv>-5.4</fme:ovs_niv>
<fme:ovs_coe>0.8</fme:ovs_coe>
<fme:str_rch>0</fme:str_rch>
<fme:bws_gem>-5.2</fme:bws_gem>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>2</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140182.399999999 489885.5</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:Overstort_Knoop_point>
</gml:featureMember>
<gml:featureMember>
""",
        ],
        UitlaatMetKeerklep: [
            """\
<gml:featureMember>
<fme:UitlaatMetKeerklep_Knoop_point gml:id="idaacef2b1-5a53-49ce-ad05-df29e5fd7458">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*UIT</fme:ide_rec>
<fme:ide_kn1>0000Weir_4</fme:ide_kn1>
<fme:ovs_bre>1</fme:ovs_bre>
<fme:ovs_niv>-5.45</fme:ovs_niv>
<fme:ovs_coe>0.8</fme:ovs_coe>
<fme:str_rch>0</fme:str_rch>
<fme:bws_gem>-5.2</fme:bws_gem>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>1</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140215.300000001 490050.800000001</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:UitlaatMetKeerklep_Knoop_point>
</gml:featureMember>
<gml:featureMember>
""",
            """\
<fme:UitlaatMetKeerklep_Knoop_point gml:id="id8fdd1163-1939-4da5-a0d0-2ae5e2040ae8">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:ide_rec>*UIT</fme:ide_rec>
<fme:ide_kn1>0000Weir_3</fme:ide_kn1>
<fme:ovs_bre>1</fme:ovs_bre>
<fme:ovs_niv>-5.4</fme:ovs_niv>
<fme:ovs_coe>0.8</fme:ovs_coe>
<fme:str_rch>0</fme:str_rch>
<fme:bws_gem>-5.2</fme:bws_gem>
<fme:gml_geometry_property>pointProperty</fme:gml_geometry_property>
<fme:Object_ID>2</fme:Object_ID>
<gml:pointProperty>
<gml:Point srsName="EPSG:28992" srsDimension="2">
<gml:pos>140182.399999999 489885.5</gml:pos>
</gml:Point>
</gml:pointProperty>
</fme:UitlaatMetKeerklep_Knoop_point>
</gml:featureMember>
<gml:featureMember>
""",
        ],
        DWAVerloopPerInwoner: [
            """\
<gml:featureMember>
<fme:DWAVerloopPerInwoner gml:id="id%(gml__id)s">
<fme:fid>0</fme:fid>
<fme:objectid>0</fme:objectid>
<fme:opmerking></fme:opmerking>
<fme:ide_rec>*DWA</fme:ide_rec>
<fme:inw_won></fme:inw_won>
<fme:dwa_con></fme:dwa_con>
<fme:dwa_u00>1.5</fme:dwa_u00>
<fme:dwa_u01>1.5</fme:dwa_u01>
<fme:dwa_u02>1.5</fme:dwa_u02>
<fme:dwa_u03>1.5</fme:dwa_u03>
<fme:dwa_u04>1.5</fme:dwa_u04>
<fme:dwa_u05>3.0</fme:dwa_u05>
<fme:dwa_u06>4.0</fme:dwa_u06>
<fme:dwa_u07>5.0</fme:dwa_u07>
<fme:dwa_u08>6.0</fme:dwa_u08>
<fme:dwa_u09>6.5</fme:dwa_u09>
<fme:dwa_u10>7.5</fme:dwa_u10>
<fme:dwa_u11>8.5</fme:dwa_u11>
<fme:dwa_u12>7.5</fme:dwa_u12>
<fme:dwa_u13>6.5</fme:dwa_u13>
<fme:dwa_u14>6.0</fme:dwa_u14>
<fme:dwa_u15>5.0</fme:dwa_u15>
<fme:dwa_u16>5.0</fme:dwa_u16>
<fme:dwa_u17>5.0</fme:dwa_u17>
<fme:dwa_u18>4.0</fme:dwa_u18>
<fme:dwa_u19>3.5</fme:dwa_u19>
<fme:dwa_u20>3.0</fme:dwa_u20>
<fme:dwa_u21>2.5</fme:dwa_u21>
<fme:dwa_u22>2.0</fme:dwa_u22>
<fme:dwa_u23>2.0</fme:dwa_u23>
<fme:dwa_typ></fme:dwa_typ>
<fme:dwa_tot></fme:dwa_tot>
<fme:dwa_def></fme:dwa_def>
</fme:DWAVerloopPerInwoner>
</gml:featureMember>"""
        ],
    },
    "XSD": {
        Knoop: """\
<element name="Knoop" type="fme:Knoop" substitutionGroup="gml:_Feature"/>
<complexType name="Knoop">
<complexContent>
<extension base="gml:AbstractFeatureType">
<sequence>
<element name="fid" minOccurs="0" type="integer"/>
<element name="objectid" minOccurs="0" type="integer"/>
<element name="opmerking" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="50"/>
</restriction>
</simpleType>
</element>
<element name="ide_rec" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="4"/>
</restriction>
</simpleType>
</element>
<element name="ide_geb" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="3"/>
</restriction>
</simpleType>
</element>
<element name="ide_knp" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="10"/>
</restriction>
</simpleType>
</element>
<element name="knp_xco" minOccurs="0" type="double"/>
<element name="knp_yco" minOccurs="0" type="double"/>
<element name="mvd_niv" minOccurs="0" type="double"/>
<element name="mvd_sch" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="wos_opp" minOccurs="0" type="integer"/>
<element name="pro_mat" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="knp_bre" minOccurs="0" type="double"/>
<element name="knp_len" minOccurs="0" type="double"/>
<element name="knp_vrm" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="knp_bok" minOccurs="0" type="double"/>
<element name="afv_hel" minOccurs="0" type="integer"/>
<element name="afv_vla" minOccurs="0" type="integer"/>
<element name="afv_vlu" minOccurs="0" type="integer"/>
<element name="loz_con" minOccurs="0" type="double"/>
<element name="aan_won" minOccurs="0" type="integer"/>
<element name="aan_inw" minOccurs="0" type="integer"/>
<element name="dwa_def" minOccurs="0">\n<simpleType>\n<restriction base="string">\n<maxLength value="40"/>\n</restriction>\n</simpleType>\n</element>
<element ref="gml:pointProperty" minOccurs="0"/>
<element ref="gml:multiPointProperty" minOccurs="0"/>
</sequence>
</extension>
</complexContent>
</complexType>""",
        GeslotenLeiding: """\
<element name="GeslotenLeiding" type="fme:GeslotenLeiding" substitutionGroup="gml:_Feature"/>
<complexType name="GeslotenLeiding">
<complexContent>
<extension base="gml:AbstractFeatureType">
<sequence>
<element name="fid" minOccurs="0" type="integer"/>
<element name="objectid" minOccurs="0" type="integer"/>
<element name="opmerking" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="50"/>
</restriction>
</simpleType>
</element>
<element name="ide_rec" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="4"/>
</restriction>
</simpleType>
</element>
<element name="ide_geb" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="3"/>
</restriction>
</simpleType>
</element>
<element name="ide_kn1" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="10"/>
</restriction>
</simpleType>
</element>
<element name="ide_gb2" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="3"/>
</restriction>
</simpleType>
</element>
<element name="ide_kn2" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="10"/>
</restriction>
</simpleType>
</element>
<element name="num_mvb" minOccurs="0" type="integer"/>
<element name="bob_kn1" minOccurs="0" type="double"/>
<element name="bob_kn2" minOccurs="0" type="double"/>
<element name="lei_len" minOccurs="0" type="double"/>
<element name="lei_typ" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="pro_mat" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="mat_sdr" minOccurs="0" type="integer"/>
<element name="pro_bre" minOccurs="0" type="double"/>
<element name="pro_hgt" minOccurs="0" type="double"/>
<element name="pro_vrm" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="pro_num" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="3"/>
</restriction>
</simpleType>
</element>
<element name="afv_een" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="afv_hel" minOccurs="0" type="double"/>
<element name="afv_vla" minOccurs="0" type="double"/>
<element name="afv_vlu" minOccurs="0" type="double"/>
<element name="aan_won" minOccurs="0" type="integer"/>
<element name="aan_inw" minOccurs="0" type="integer"/>
<element name="pro_knw" minOccurs="0" type="double"/>
<element name="str_rch" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="inv_kn1" minOccurs="0" type="double"/>
<element name="uit_kn1" minOccurs="0" type="double"/>
<element name="inv_kn2" minOccurs="0" type="double"/>
<element name="uit_kn2" minOccurs="0" type="double"/>
<element name="qdh_num" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>
<element name="qdh_niv" minOccurs="0" type="double"/>
<element name="nsh_frt" minOccurs="0" type="integer"/>
<element name="nsh_frv" minOccurs="0" type="double"/>
<element name="dwa_def" minOccurs="0">\n<simpleType>\n<restriction base="string">\n<maxLength value="40"/>\n</restriction>\n</simpleType>\n</element>
<element name="nsh_upt" minOccurs="0" type="integer"/>
<element name="nsh_upn" minOccurs="0">\n<simpleType>\n<restriction base="string">\n<maxLength value="40"/>\n</restriction>\n</simpleType>\n</element>
<element ref="gml:curveProperty" minOccurs="0"/>
<element ref="gml:multiCurveProperty" minOccurs="0"/>
</sequence>
</extension>
</complexContent>
</complexType>""",
    },
}


class ObjectCreateTest(unittest.TestCase):
    "testing HydroObject creation"

    def test0Pass(self):
        "testing creation from SUF-HYD data"

    def test1CreationGeslotenLeiding(self):
        "- just if GeslotenLeiding is created"
        repr = sampleStrings["SUFHYD"][GeslotenLeiding][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, GeslotenLeiding)

    def test1CreationKnoop(self):
        "- just if Knoop is created"
        repr = sampleStrings["SUFHYD"][Knoop][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Knoop)
        repr = sampleStrings["SUFHYD"][Knoop][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Knoop)

    def test1CreationGemaal(self):
        "- just if Gemaal is created"
        repr = sampleStrings["SUFHYD"][Gemaal][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        assert isinstance(obj, Gemaal)

    def test1CreationGemaal1(self):
        "- just if Gemaal (Knoop) is created"
        repr = sampleStrings["SUFHYD"][Gemaal][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Gemaal_Knoop)

    def test1CreationGemaal2(self):
        "- just if Gemaal (Tak) is created"
        repr = sampleStrings["SUFHYD"][Gemaal][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Gemaal_Tak)

    def test1CreationOverstort1(self):
        "- just if Overstort (Knoop) is created"
        repr = sampleStrings["SUFHYD"][Overstort][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Overstort_Knoop)

    def test1CreationOverstort1a(self):
        "- Overstort (Knoop) is created from object that incorrectly gives gb2 and no kn2"
        repr = sampleStrings["SUFHYD"][Overstort][10]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Overstort_Knoop)

    def test1CreationOverstort2(self):
        "- just if Overstort (Tak) is created"
        repr = sampleStrings["SUFHYD"][Overstort][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, Overstort_Tak)

    def test1CreationUitlaatMetKeerklep1(self):
        "- just if UitlaatMetKeerklep (Knoop) is created"
        repr = sampleStrings["SUFHYD"][UitlaatMetKeerklep][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, UitlaatMetKeerklep_Knoop)

    def test1CreationUitlaatMetKeerklep2(self):
        "- just if UitlaatMetKeerklep (Tak) is created"
        repr = sampleStrings["SUFHYD"][UitlaatMetKeerklep][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, UitlaatMetKeerklep_Tak)

    def test1CreationAfvoerendOppervlak1(self):
        "- just if AfvoerendOppervlak (Knoop) is created"
        repr = sampleStrings["SUFHYD"][AfvoerendOppervlak][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, AfvoerendOppervlak_Knoop)

    def test1CreationAfvoerendOppervlak2(self):
        "- just if AfvoerendOppervlak (Tak) is created"
        repr = sampleStrings["SUFHYD"][AfvoerendOppervlak][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.__class__, AfvoerendOppervlak_Tak)

    def test1CreationZ(self):
        "- batch testing creation"
        for i in sum(list(sampleStrings["SUFHYD"].values()), []):
            HydroObjectFactory.hydroObjectFromSUFHYD(i)

    def test2Fields(self):
        "- if Knoop got the string fields"
        repr = sampleStrings["SUFHYD"][Knoop][3]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.fields["ide_knp"], "0000NUENEN")
        self.assertEqual(obj.fields["ide_geb"], "   ")
        self.assertEqual(obj.fields["knp_xco"], "  166060600")

    def test3Attribs(self):
        "- if Knoop has the correct attributes"
        repr = sampleStrings["SUFHYD"][Knoop][3]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.ide_knp, "0000NUENEN")
        self.assertEqual(obj.ide_geb, "")
        self.assertEqual(obj.knp_xco, 166060600)

    def test40AttribKnoop_afv_hel(self):
        "- if Knoop has integer afv_hel"
        repr = sampleStrings["SUFHYD"][Knoop][11]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.afv_hel, 0)

    def test42AttribGeslotenLeiding_afv_hel(self):
        "- if GeslotenLeiding has float afv_hel"
        repr = sampleStrings["SUFHYD"][GeslotenLeiding][10]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.afv_hel, 0.0)

    def test43AttribGeslotenLeiding_unknown(self):
        "- if GeslotenLeiding hellevoetsluis"
        repr = sampleStrings["SUFHYD"][GeslotenLeiding][11]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.afv_hel, 0.0)

    def test44AttribGeslotenLeiding_space_in_id(self):
        "- if GeslotenLeiding accepts space in id"
        repr = sampleStrings["SUFHYD"][GeslotenLeiding][12]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(repr)
        self.assertEqual(obj.ide_kn2, "000 GLDRP")

    def test5ReproduceAfvoerendOppervlak(self):
        "- if AfvoerendOppervlak knows how to represent itself"
        input = sampleStrings["SUFHYD"][AfvoerendOppervlak][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceBergendOppervlakKnoop(self):
        "- if BergendOppervlak knows how to represent itself"
        input = sampleStrings["SUFHYD"][BergendOppervlakKnoop][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceDoorlaat(self):
        "- if Doorlaat knows how to represent itself"
        input = sampleStrings["SUFHYD"][Doorlaat][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceGemaal(self):
        "- if Gemaal knows how to represent itself"
        input = sampleStrings["SUFHYD"][Gemaal][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceGemaalMultiPump(self):
        "- if Gemaal (more than one pump) knows how to represent itself"
        for input in sampleStrings["SUFHYD"][Gemaal]:
            obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
            output = obj.toSufHyd()
            self.assertEqual(input.strip(), output.strip())

    def test5ReproduceGeslotenLeiding(self):
        "- if GeslotenLeiding knows how to represent itself"
        input = sampleStrings["SUFHYD"][GeslotenLeiding][4]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        output = output.strip()
        input = input.strip()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceKnoop(self):
        "- if Knoop knows how to represent itself"
        input = sampleStrings["SUFHYD"][Knoop][2]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceOverstort(self):
        "- if Overstort (Knoop) knows how to represent itself"
        input = sampleStrings["SUFHYD"][Overstort][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceOverstort1(self):
        "- if Overstort (Tak) knows how to represent itself"
        input = sampleStrings["SUFHYD"][Overstort][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceUitlaatMetKeerklep(self):
        "- if UitlaatMetKeerklep (Knoop) knows how to represent itself"
        input = sampleStrings["SUFHYD"][UitlaatMetKeerklep][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceUitlaatMetKeerklep1(self):
        "- if UitlaatMetKeerklep (Tak) knows how to represent itself"
        input = sampleStrings["SUFHYD"][UitlaatMetKeerklep][1]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceOverstortShort(self):
        "- if the last field is recognized"
        input = sampleStrings["SUFHYD"][Overstort][0].strip()
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test5ReproduceDWAVerloopPerInwoner(self):
        "- if DWAVerloopPerInwoner knows how to represent itself"
        for input in sampleStrings["SUFHYD"][DWAVerloopPerInwoner]:
            obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
            output = obj.toSufHyd()
            self.assertEqual(input.strip(), output.strip())

    def test4CreatingDummyEnd(self):
        "- if we can create an End object without having any string to parse"

        obj = End()
        self.assertEqual(obj.__class__, End)
        self.assertEqual(obj.toSufHyd().strip(), "*END")

    def test4CreationAlgemeneInformatie1(self):
        "- only one AlgemeneInformatie is created from multiple lines"
        repr = "\n".join(sampleStrings["SUFHYD"][AlgemeneInformatie])
        objlist = HydroObjectFactory.hydroObjectListFromSUFHYD(repr)
        self.assertEqual(len(objlist), 1)
        self.assertEqual(objlist[0].__class__, AlgemeneInformatie)

    def test4CreationAlgemeneInformatie2(self):
        "- the single AlgemeneInformatie contains all information"
        # just get the object that we know we can create!
        repr = "\n".join(
            [i.strip() for i in sampleStrings["SUFHYD"][AlgemeneInformatie]]
        )
        obj = HydroObjectFactory.hydroObjectListFromSUFHYD(repr)[0]
        [k for k in AlgemeneInformatie.field_names if isSufHydKey(k)]
        self.assertEqual(obj.alg_dat, "20050315")
        self.assertEqual(obj.alg_opd, "")
        self.assertEqual(obj.alg_uit, "")
        self.assertEqual(obj.alg_oms, "dwa")
        self.assertEqual(obj.alg_ove, r"exported from Sobek D:\Sobek\EHOVEN.lit\3")

    def test61UnreadableCausesException0(self):
        "- unknown sufhyd line causes RuntimeError"
        input = "this is not a sufhyd line"
        self.assertRaises(RuntimeError, HydroObjectFactory.hydroObjectFromSUFHYD, input)

    def test62UnreadableCausesException1(self):
        "- GeslotenLeiding can't be generated from *KNP"
        input = sampleStrings["SUFHYD"][Knoop][0]
        self.assertRaises(RuntimeError, GeslotenLeiding, "SUFHYD", input)

    def test63UnreadableCausesException2(self):
        "- wrong sufhyd line causes RuntimeError"
        handler.flush()
        input = "*OVS       J1907W                 3       17.8  0.941 16..45"
        self.assertRaises(RuntimeError, HydroObjectFactory.hydroObjectFromSUFHYD, input)
        self.assertEqual(len(handler.content), 1)

    def test63UnreadableCausesException4(self):
        "- wrong sufhyd line causes RuntimeError"
        handler.flush()
        input = "*KNP 8484560                                             -1.00      100            0.008 01 "
        self.assertRaises(RuntimeError, HydroObjectFactory.hydroObjectFromSUFHYD, input)
        self.assertEqual(len(handler.content), 1)

    def test64NonBlockingUnreadable(self):
        "- do not stop when seeing an unreadable line"
        handler.flush()
        input = []
        input.extend(sampleStrings["SUFHYD"][Knoop])
        input.append("*OVS       J1907W                 3       17.8  0.941 16..45")
        input.extend(sampleStrings["SUFHYD"][GeslotenLeiding])
        input.append("*END")
        input_str = "\n".join(input)
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(input_str)
        self.assertEqual(
            len(obj_list),
            len(sampleStrings["SUFHYD"][Knoop])
            + len(sampleStrings["SUFHYD"][GeslotenLeiding])
            + 1,
        )
        self.assertEqual(len(handler.content), 3)

    def test650ReportingUnreadable(self):
        "- the unreadable line is reported (WARNING), no class so no split"
        handler.flush()
        input = []
        input.extend(sampleStrings["SUFHYD"][Knoop])
        input.append(" *OVS       J1907W                 3       17.8  0.941 16..45")
        input.extend(sampleStrings["SUFHYD"][GeslotenLeiding])
        input.append("*END")
        input_str = "\n".join(input)

        handler.flush()
        HydroObjectFactory.hydroObjectListFromSUFHYD(input_str)
        expect = " *OVS       J1907W                 3       17.8  0.941 16..45"
        records = [i for i in handler.content if i.find(expect) != -1]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].split("|")[1], "WARNING")

    def test651ReportingUnreadable(self):
        "- the unreadable line is reported (WARNING), split according to most likely class"
        input = []
        input.extend(sampleStrings["SUFHYD"][Knoop])
        input.append("*OVS       J1907W                 3       17.8  0.941 16..45")
        input.extend(sampleStrings["SUFHYD"][GeslotenLeiding])
        input.append("*END")
        input_str = "\n".join(input)

        handler.flush()
        HydroObjectFactory.hydroObjectListFromSUFHYD(input_str)
        expect = "|*OVS|   |    J1907W|   |          |  |  3    |   17.8 | 0.941| 1|6.|.45||||||"
        records = [i for i in handler.content if i.find(expect) != -1]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].split("|")[1], "WARNING")

    def test66ReportingUnreadableGeometry(self):
        "- if geometry makes use of non existent nodes it is logged as WARNING"
        input = []
        input.extend(sampleStrings["SUFHYD"][Knoop][:-6])
        input.extend(sampleStrings["SUFHYD"][GeslotenLeiding])
        input.append("*END")
        input_str = "\n".join(input)

        handler.flush()
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(input_str)
        HydroObjectFactory.propagateGeometries(obj_list)
        expect = "*LEI:0000K16618->0000K16620"
        records = [i for i in handler.content if i.find(expect) != -1]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].split("|")[1], "WARNING")

    def test70ObjectsHaveStartPointId(self):
        "- all objects have a get_start_pointId"
        for thisClass in list(sampleStrings["SUFHYD"].keys()):
            obj = HydroObjectFactory.hydroObjectFromSUFHYD(
                sampleStrings["SUFHYD"][thisClass][0]
            )
            obj.get_start_pointId()

    def test71VertexNameDoesNotGetLeadingZeroes(self):
        "- a vertex name shorter than 10 is NOT padded with leading zeroes - ticket 151"
        input = "*OVS      BYPASS2                33       3     0.941   1   10.40"
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        self.assertEqual(obj.get_start_pointId(), "BYPASS2")

    def test72VertexNameCanBeJustAreaCode(self):
        "- a destination vertex name with just area code is empty - ticket 150"
        input = "*OVS 00   BYPASS2 00             33       3     0.941   1   10.40"
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        self.assertEqual(obj.get_start_pointId(), "00_BYPASS2")
        self.assertEqual(obj.get_end_pointId(), "")
        self.assertEqual(obj.__class__, Overstort_Knoop)


class FileReadTest(unittest.TestCase):
    "testing reading sequence of HydroObject objects"

    input = """\
*KNP   0000NOORD1                 164371100  388463700   19.14  0   100   100.000        00    5.00
*KNP   0000NOORD2                 163804600  385965500   19.14  0   100   100.000        00    2.00
*KNP   000RWZINRD                 162964800  385605500   15.41  0   100     1.000        00    8.00
*KNP   0000NUENEN                 166060600  386760700   19.14  0   100    36.742        00    6.14
*KNP   000NUENEN2                 166065600  386760700   19.14  0   100     4.000        00    6.14
*LEI   0000NOORD1   0000NOORD2      5.00    2.002561.63           1.500  2.000 02
*LEI   0000NOORD2   000RWZINRD      2.00    1.00 999.00           1.500  2.000 02
*LEI   0000NUENEN   000NUENEN2      6.14    6.14  50.00           1.000        04
*END
"""

    def test0Pass(self):
        "testing reading/writing sequence of HydroObject objects"

    def test1ReadingSequence(self):
        "- if a sequence of lines is read into equal sized sequence of objects"

        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.input)
        self.assertEqual(len(obj_list), 9)

    def test2ReadingSequence(self):
        "- if a sequence of lines is read into corresponding sequence of objects"

        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.input)
        obj_types = [
            Knoop,
            Knoop,
            Knoop,
            Knoop,
            Knoop,
            GeslotenLeiding,
            GeslotenLeiding,
            GeslotenLeiding,
            End,
        ]
        for i, j in map(None, obj_list, obj_types):
            self.assertEqual(i.__class__, j)

    def test3ReproducingSequence(self):
        "- reading a sequence of lines and comparing the representation"

        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.input)
        obj_str_list = re.split("[\n\r]+", self.input)
        for i, j in map(None, obj_list, obj_str_list):
            if i:
                output = i.toSufHyd()
            else:
                output = ""
            self.assertEqual(output.strip(), j.strip())


class ObjectCreateFromGMLTest(unittest.TestCase):
    "testing HydroObject creation"
    geslotenLeiding = sampleStrings["GML"][GeslotenLeiding][0]

    def test0Pass(self):
        "testing creation from GML data"
        pass

    def test1CreateKnoop(self):
        "- can I choose the correct class (Knoop)?"
        obj = HydroObjectFactory.hydroObjectFromGML(sampleStrings["GML"][Knoop][0])
        self.assertEqual(obj.__class__, Knoop)

    def test1CreateGeslotenLeiding(self):
        "- can I choose the correct class (GeslotenLeiding)?"
        obj = HydroObjectFactory.hydroObjectFromGML(
            sampleStrings["GML"][GeslotenLeiding][0]
        )
        self.assertEqual(obj.__class__, GeslotenLeiding)

    def test2CreateGeslotenLeiding(self):
        "- are GeslotenLeiding string fields read correctly?"
        obj = HydroObjectFactory.hydroObjectFromGML(
            sampleStrings["GML"][GeslotenLeiding][0]
        )
        self.assertEqual(obj.fields["bob_kn2"], "2.00")

    def test2CreateKnoop(self):
        "- are Knoop string fields read correctly?"
        obj = HydroObjectFactory.hydroObjectFromGML(sampleStrings["GML"][Knoop][0])
        self.assertEqual(obj.fields["knp_xco"], "164371.100")

    def test3CreateGeslotenLeiding(self):
        "- are GeslotenLeiding attributes read correctly?"
        obj = HydroObjectFactory.hydroObjectFromGML(
            sampleStrings["GML"][GeslotenLeiding][0]
        )
        self.assertEqual(obj.bob_kn2, 2.00)

    def test3CreateKnoop(self):
        "- are Knoop attributes read correctly?"
        obj = HydroObjectFactory.hydroObjectFromGML(sampleStrings["GML"][Knoop][0])
        self.assertEqual(obj.knp_xco, 164371100)

    def test4CreateKnoopIntegerCoordinate(self):
        "- are Knoop coordinates read correctly even if integer valued?"
        obj = HydroObjectFactory.hydroObjectFromGML(sampleStrings["GML"][Knoop][3])
        self.assertEqual(obj.knp_yco, 490003000)

    def test4CreateTakGemaal(self):
        "- does Gemaal_Tak know of its end point?"
        obj = HydroObjectFactory.hydroObjectFromGML(sampleStrings["GML"][Gemaal][1])
        self.assertEqual(obj.__class__, Gemaal_Tak)
        self.assertEqual(obj.ide_kn2, "0000DWA_72")

    def test4CreateTakAfvoerendOppervlak(self):
        "- does AfvoerendOppervlak_Tak know of its end point?"
        obj = HydroObjectFactory.hydroObjectFromGML(
            sampleStrings["GML"][AfvoerendOppervlak][1]
        )
        self.assertEqual(obj.__class__, AfvoerendOppervlak_Tak)
        self.assertEqual(obj.ide_kn2, "0000DWA_56")


class GMLFileReadTest(unittest.TestCase):
    "testing HydroObject creation"

    def test0Pass(self):
        "testing creation from GML file"
        pass

    def test1ReadingSequence(self):
        "- do we get a correctly sized sequence?"
        handler.flush()
        handler.setLevel(logging.ERROR)
        fakeFile = "\n".join(sum(list(sampleStrings["GML"].values()), []) * 4)
        obj_list = HydroObjectFactory.hydroObjectListFromGML(fakeFile)
        self.assertEqual(
            len(obj_list), len(sum(list(sampleStrings["GML"].values()), [])) * 4
        )
        self.assertEqual(handler.content, [])
        handler.setLevel(logging.DEBUG)

    def test2ReadingSequence(self):
        "- do we get a sequence with the correct types?"
        fakeFile = (
            sampleStrings["GML"][Knoop][0] + sampleStrings["GML"][GeslotenLeiding][0]
        ) * 4
        expected = [Knoop, GeslotenLeiding] * 4
        obj_list = HydroObjectFactory.hydroObjectListFromGML(fakeFile)
        for i, j in map(None, obj_list, expected):
            self.assertEqual(i.__class__, j)

    def test3inconsistentInput(self):
        "- do we notice inconsistent ide_rec/fme:<type>?"
        fakeFile = """\
<gml:featureMember>
<fme:AfvoerendOppervlak_Tak gml:id="id6d8bd245-d54f-4d62-906c-24e8515b157b">
<fme:OBJECTID_1>1</fme:OBJECTID_1>
<fme:FID_leid_s>38</fme:FID_leid_s>
<fme:fid_>0</fme:fid_>
<fme:objectid>0</fme:objectid>
<fme:opmerking> </fme:opmerking>
<fme:ide_rec>*LEI</fme:ide_rec>
</fme:AfvoerendOppervlak_Tak>
</gml:featureMember>
"""
        handler.flush()
        HydroObjectFactory.hydroObjectListFromGML(fakeFile)
        # self.assertEqual(obj_list, [])
        expect = "does not match declared fme:"
        records = [i for i in handler.content if i.find(expect) != -1]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].split("|")[1], "WARNING")


class GMLElementFromDescription(unittest.TestCase):
    def test0Pass(self):
        "testing generation of element describing a field"
        pass

    def test1AtomicTypeInt(self):
        '- xsd: type is int, expect "integer"'

        e = GmlElement("aan_inw", int, 4)
        self.assertEqual(
            e.toxsd(), '<element name="aan_inw" minOccurs="0" type="integer"/>'
        )
        pass

    def test1AtomicTypeFloat(self):
        '- xsd: type is float, expect "double"'

        e = GmlElement("lei_len", float, 7, 2)
        self.assertEqual(
            e.toxsd(), '<element name="lei_len" minOccurs="0" type="double"/>'
        )
        pass

    def test1SimpleTypeString(self):
        "- xsd: type is str, expect simpleElement plus restriction..."
        e = GmlElement("lei_typ", str, 2)
        self.assertEqual(
            e.toxsd(),
            """\
<element name="lei_typ" minOccurs="0">
<simpleType>
<restriction base="string">
<maxLength value="2"/>
</restriction>
</simpleType>
</element>""",
        )
        pass

    def test2AtomicTypeInt(self):
        "- checking xml representation of integer value"

        e = GmlElement("aan_inw", int, 4)
        e.setValue(25)
        self.assertEqual(e.toxml(), "<fme:aan_inw>25</fme:aan_inw>")
        pass

    def test2AtomicTypeFloat(self):
        "- checking xml representation of floating value"

        e = GmlElement("lei_len", float, 7, 2)
        e.setValue(40.02)
        self.assertEqual(e.toxml(), "<fme:lei_len>40.02</fme:lei_len>")
        pass

    def test2AtomicTypeFloatRounded(self):
        "- checking xml representation of floating value - with rounding error"

        e = GmlElement("lei_len", float, 7, 2)
        e.setValue(40.0199996)
        self.assertEqual(e.toxml(), "<fme:lei_len>40.02</fme:lei_len>")
        pass

    def test2SimpleTypeString(self):
        "- checking xml representation of string value"
        e = GmlElement("lei_typ", str, 2)
        e.setValue("RW")
        self.assertEqual(e.toxml(), "<fme:lei_typ>RW</fme:lei_typ>")
        pass

    def test3KnoopXsdRepresentation(self):
        """- complete xsd representation of Knoop"""
        obj = Knoop(
            "SUFHYD",
            "*KNP   0000NOORD1                 164371100  388463700   19.14  0   100   100.000        00    5.00                   ",
        )
        self.assertEqual(obj.toxsd(), sampleStrings["XSD"][Knoop])
        pass

    def test3GeslotenLeidingXsdRepresentation(self):
        """- complete xsd representation of GeslotenLeiding"""
        obj = GeslotenLeiding(
            "SUFHYD",
            "*LEI   0000NOORD1   0000NOORD2      5.00    2.002561.63           1.500  2.000 02                                      ",
        )
        self.assertEqual(obj.toxsd(), sampleStrings["XSD"][GeslotenLeiding])
        pass


class GMLTextProductionSingleObjectTest(unittest.TestCase):
    sufhyd_knoop = sampleStrings["SUFHYD"][Knoop][0]
    gml_knoop = sampleStrings["GML"][Knoop][1]

    def test0Pass(self):
        "testing production of gml data"
        pass

    def test1AlmostEmptyKnoop(self):
        "- a 'Knoop' object with very few attributes"

        obj = Knoop("SUFHYD", sampleStrings["SUFHYD"][Knoop][0])
        self.assertEqual(obj.toxml(), sampleStrings["GML"][Knoop][0] % obj.__dict__)

    def test1AlmostEmptyGeslotenLeiding(self):
        "- a 'GeslotenLeiding' object with very few attributes"

        obj = GeslotenLeiding("SUFHYD", sampleStrings["SUFHYD"][GeslotenLeiding][0])
        self.assertEqual(
            obj.toxml(), sampleStrings["GML"][GeslotenLeiding][0] % obj.__dict__
        )

    def test2DWAVerloopPerInwoner(self):
        "- a 'DWAVerloopPerInwoner' object with all attributes"

        obj = DWAVerloopPerInwoner(
            "SUFHYD", sampleStrings["SUFHYD"][DWAVerloopPerInwoner][0]
        )
        self.assertEqual(
            obj.toxml(), sampleStrings["GML"][DWAVerloopPerInwoner][0] % obj.__dict__
        )

    def test2GemaalVertexHasGeoproperties(self):
        "- a 'Gemaal' (Vertex) has Vertex geoproperties"

        HydroObjectFactory.hydroObjectListFromSUFHYD(sampleStrings["SUFHYD"][Gemaal][0])
        # obj.


class GMLConsistentNetworkTest(unittest.TestCase):
    elem_list = (
        sampleStrings["SUFHYD"][Knoop] + sampleStrings["SUFHYD"][GeslotenLeiding]
    )
    fake_file = "\n".join(elem_list)

    def test0Pass(self):
        "production of gml data for a network with Knoop and GeslotenLeidingen"
        pass

    def test1ReadingTheData(self):
        "- is the data read at all?"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.fake_file)
        self.assertEqual(len(obj_list), len(self.elem_list))
        pass

    def test2DoEdgeElementsKnowAboutTheirExtremePoints(self):
        "- do edge elements know about their extreme points?"
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(
            sampleStrings["SUFHYD"][GeslotenLeiding][0]
        )
        self.assertEqual(obj.__class__, GeslotenLeiding)
        self.assertEqual(obj.get_start_pointId(), "0000NOORD1")
        self.assertEqual(obj.get_end_pointId(), "0000NOORD2")

        obj = HydroObjectFactory.hydroObjectFromSUFHYD(
            sampleStrings["SUFHYD"][Gemaal][0]
        )
        self.assertEqual(obj.__class__, Gemaal_Tak)
        self.assertEqual(obj.get_start_pointId(), "0000B1436F")
        self.assertEqual(obj.get_end_pointId(), "0000C1677D")

    def test3PropagatingTheGeometricalProperties(self):
        "- can we propagate the geometrical properties?"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.fake_file)
        self.assertEqual(HydroObjectFactory.propagateGeometries(obj_list), True)
        pass

    def test4TwoNodesOneEdge(self):
        "- N-E-N: do we find node coordinates in edges?"
        n1 = HydroObjectFactory.hydroObjectFromSUFHYD(sampleStrings["SUFHYD"][Knoop][0])
        n2 = HydroObjectFactory.hydroObjectFromSUFHYD(sampleStrings["SUFHYD"][Knoop][1])
        e = HydroObjectFactory.hydroObjectFromSUFHYD(
            sampleStrings["SUFHYD"][GeslotenLeiding][0]
        )
        obj_list = [n1, n2, e]
        for obj in [i for i in obj_list if isinstance(i, GeslotenLeiding)]:
            self.assertEqual(type(obj.kn1_xco_m), type(0.0))
            self.assertEqual(type(obj.kn1_yco_m), type(0.0))
            self.assertEqual(type(obj.kn2_xco_m), type(0.0))
            self.assertEqual(type(obj.kn2_yco_m), type(0.0))
        self.assertEqual(e.kn1_xco_m, 0)
        self.assertEqual(e.kn1_yco_m, 0)
        self.assertEqual(e.kn2_xco_m, 0)
        self.assertEqual(e.kn2_yco_m, 0)
        HydroObjectFactory.propagateGeometries(obj_list)
        self.assertEqual(e.kn1_xco_m, 164371.100)
        self.assertEqual(e.kn1_yco_m, 388463.700)
        self.assertEqual(e.kn2_xco_m, 163804.600)
        self.assertEqual(e.kn2_yco_m, 385965.500)

    def test5MoreComplexGraph(self):
        "- more complex graph: do we find node coordinates in edges?"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.fake_file)
        for obj in [i for i in obj_list if isinstance(i, GeslotenLeiding)]:
            self.assertEqual(type(obj.kn1_xco_m), type(0.0))
            self.assertEqual(type(obj.kn1_yco_m), type(0.0))
            self.assertEqual(type(obj.kn2_xco_m), type(0.0))
            self.assertEqual(type(obj.kn2_yco_m), type(0.0))
        for obj in [i for i in obj_list if isinstance(i, GeslotenLeiding)]:
            self.assertEqual(obj.kn1_xco_m, 0.0)
            self.assertEqual(obj.kn1_yco_m, 0.0)
            self.assertEqual(obj.kn2_xco_m, 0.0)
            self.assertEqual(obj.kn2_yco_m, 0.0)
        HydroObjectFactory.propagateGeometries(obj_list, strict=True)
        for obj in [i for i in obj_list if isinstance(i, GeslotenLeiding)]:
            self.assertNotEqual(obj.kn1_xco_m, 0.0)
            self.assertNotEqual(obj.kn1_yco_m, 0.0)
            self.assertNotEqual(obj.kn2_xco_m, 0.0)
            self.assertNotEqual(obj.kn2_yco_m, 0.0)


class GMLWritingFiles(unittest.TestCase):
    elem_list = (
        sampleStrings["SUFHYD"][Knoop] + sampleStrings["SUFHYD"][GeslotenLeiding]
    )
    fake_file = "\n".join(elem_list)

    def test0pass(self):
        "write in two separate streams all xml data"
        pass

    def test1writerWritesAllParts(self):
        "- if the xsd file contains all expected parts"

        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.fake_file)
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)
        self.assertEqual(mockXsdFile.got["header"], True)
        self.assertEqual(mockXsdFile.got["schema"], True)
        self.assertEqual(mockXsdFile.got["end-decl"], None)

        self.assertEqual(mockGmlFile.got["header"], True)
        self.assertEqual(mockGmlFile.got["geometry"], True)
        self.assertEqual(mockGmlFile.got["trailer"], True)
        self.assertEqual(mockGmlFile.got["end-def"], None)


class Bug00040(unittest.TestCase):
    ticket_test = """\
*LEI 240000003047   0000003045      6.70    6.70 225.40 00                        )y                                     0
*KNP 240000003047                 236338000  560655400    8.30  0   300     1.000        00    7.20                                 0
*KNP 240000003045                 236081400  560504600    8.00  0   300     0.316        00    6.70                                 0
*KNP 200000003047                 234654800  560087600   10.98  0   300                                                             0
"""
    input = """\
*LEI 20         5            6      9.11    9.33  83.26 00                        (x                                     0
*KNP 20         6                 234654800  560087600   10.98  0   300                                                             0
*KNP 24         6                 236279500  560612100    8.00  0   300     0.316        00    6.70                                 0
*KNP 20         5                 234738000  560090900   11.14  0   300     1.000        00    9.11                                 0
"""

    def test01(self):
        "area code is part of the node id - test as of ticket 40"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)
        output = "".join(mockGmlFile.buffer)
        self.assertTrue(output.count("236338.000") >= 3)
        self.assertTrue(output.count("234654.800") >= 3)

    def test02(self):
        "- the nodes identify themselves with gebiedsarea - ticket 40"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.input)
        (knp246,) = [i for i in obj_list if i.ide_geb == "24"]
        self.assertEqual(knp246.get_start_pointId(), "24_6")

    def test03(self):
        "- nodes with similar name in different areas must be kept apart - ticket 40"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.input)
        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)
        output = "".join(mockGmlFile.buffer)
        self.assertTrue(output.count("236279.500") >= 3)
        self.assertTrue(output.count("234654.800") >= 3)
        pass


class Bug00041(unittest.TestCase):
    ticket_test = """\
*LEI 010000003092   0000003073      9.22    9.18  10.45 00                        3<                                     0
*KNP 010000003092                 234338800  558899000   10.20  0   300                                                             0
*KNP 010000003073                 234343200  558908400   10.16  0   300                                                             0
*PRO 3<  2   9.220  0.000  0.500  0.500  10.220  1.500  3.328  2.500
"""
    single_lei_no_knp = """\
*LEI 010000003092   0000003073      9.22    9.18  10.45 00                        3<                                     0
"""

    def test01(self):
        "bug00041 - test as of ticket"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)
        pro_nums = [
            i for i in "".join(mockGmlFile.buffer).split("\n") if i.count(">3<<")
        ]
        self.assertEqual(pro_nums, [])
        pro_nums = [
            i for i in "".join(mockGmlFile.buffer).split("\n") if i.count(">3&lt;<")
        ]
        self.assertEqual(
            pro_nums,
            ["<fme:pro_num>3&lt;</fme:pro_num>", "<fme:pro_num>3&lt;</fme:pro_num>"],
        )

    def test02(self):
        "bug00041 - the converter should not crash on empty input"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.single_lei_no_knp)
        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)


class uitbreidingSufHyd(unittest.TestCase):
    ticket_test = [
        "*KNP 120000001028                 232221000  556283000   10.65  0   300     0.800        00    9.45                                 0",
        "*KNP 12000000290F                 232208100  556314100   10.75  0   300     0.800        00    8.75                                 0",
        "*KNPP120000001000                 232168700  556210600   10.75  0   300     0.800        00    9.75                                 0",
        "*KNPP120000001001                 232160400  556205600   10.75  0   300     0.800        00    9.75                                 0",
        "*KNP 900000003293                 232938900  555801400   10.83  0   300                                                             0",
        "*KNP 900000003294                 232954000  555717000   10.86  0   300                                                             0dwadef..................................",
        "*LEI 120000001028 12000000290F      9.45    9.40  33.63 00 01 34  0.200        00                                        0 0.40",
        "*LEIP120000001000P120000001001      9.75    9.75   9.70    01 34  0.200        00                                        0 0.40",
        "*LEI 900000003293 900000003294      9.41    9.37  85.69 00 99                     *Q                                     0                                      3    20.00000 dwa_def-dwa_def-dwa_def-dwa_def-dwa_def-  1  name of user defined pipe...............",
        "*PRO *Q  4   9.410  0.000  0.000  0.000  10.490  1.620  3.697  3.000  10.830  3.436  8.426  7.680  10.970  4.519  8.730  7.800  ",
        "*AFK 150000003225 150000003223   m2   3241.0015.0 1.0   2   3 4.00 5.000.330                      ",
        "*INL 02 00  0.0 1.0   0   0 0.00 0.00 0.50",
        "*INL 02 01  2.0 1.0   0   0 0.00 0.00 0.20  1  1",
        "*INL 02 02  4.0 1.0   0   0 0.00 0.00 0.10",
        "*DWA 2.50 12.00  1.5  1.5  1.5  1.5  1.5  3.0  4.0  5.0  6.0  6.5  7.5  8.5  7.5  6.5  6.0  5.0  5.0  5.0  4.0  3.5  3.0  2.5  2.0  2.0   2    120.00                               Default_DWA",
    ]

    def test01(self):
        "uitbreiding SUFHYD definitie - *KNP"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(
            "\n".join(self.ticket_test[:6])
        )
        self.assertEqual(len(obj_list), 6)
        obj = obj_list[5]
        self.assertEqual(obj.toSufHyd(), self.ticket_test[5])

    def test02(self):
        "uitbreiding SUFHYD definitie - *LEI - geb(3)"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test[7])
        self.assertEqual(len(obj_list), 1)

    def test03(self):
        "uitbreiding SUFHYD definitie - *LEI - extra fields"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test[8])
        self.assertEqual(len(obj_list), 1)
        (obj,) = obj_list
        self.assertEqual(obj.toSufHyd(), self.ticket_test[8])

    def test04(self):
        "uitbreiding SUFHYD definitie - *PRO"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test[9])
        self.assertEqual(len(obj_list), 1)

    def test05(self):
        "uitbreiding SUFHYD definitie - *AFK"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test[10])
        self.assertEqual(len(obj_list), 1)
        (obj,) = obj_list
        self.assertEqual(obj.toSufHyd().strip(), self.ticket_test[10].strip())

    def test06(self):
        "uitbreiding SUFHYD definitie - *INL"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(
            "\n".join(self.ticket_test[11:14])
        )
        self.assertEqual(len(obj_list), 3)
        (o1, o2, o3) = obj_list
        self.assertEqual(o1.afv_vdp, 1.0)
        self.assertEqual(o1.afv_afs, 0.5)
        self.assertEqual(o1.afv_ind, "")
        self.assertEqual(o1.afv_inr, "")
        self.assertEqual(o2.afv_ind, 1)
        self.assertEqual(o2.afv_inr, 1)

    def test07(self):
        "uitbreiding SUFHYD definitie - *DWA"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test[14])
        self.assertEqual(len(obj_list), 1)
        (obj,) = obj_list
        self.assertEqual(obj.dwa_typ, 2)
        self.assertEqual(obj.dwa_tot, 120.0)
        self.assertEqual(obj.dwa_def, "Default_DWA")
        self.assertEqual(obj.toSufHyd(), self.ticket_test[14])

    def test08(self):
        "uitbreiding SUFHYD definitie - *INI (InitieleLeidingWaarden)"
        input = sampleStrings["SUFHYD"][InitieleLeidingWaarden][0]
        obj = HydroObjectFactory.hydroObjectFromSUFHYD(input)
        output = obj.toSufHyd()
        self.assertEqual(input.strip(), output.strip())

    def test51(self):
        "uitbreiding SUFHYD definitie - summarizing"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(
            "\n".join(self.ticket_test), strict=False
        )
        self.assertEqual(len(obj_list), 15)
        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)


class twoPointsAtSameCoordinates(unittest.TestCase):
    ticket_test = [
        "*KNP 120000001028                 232221000  556283000   10.65  0   300     0.800        00    9.45                                 0",
        "*KNP 12000000290F                 232221000  556283000   10.75  0   300     0.800        00    8.75                                 0",
        "*KNP 120000001000                 232168700  556210600   10.75  0   300     0.800        00    9.75                                 0",
        "*LEI 120000001028 12000000290F      9.45    9.40  33.63 00 01 34  0.200        00                                        0 0.40",
        "*LEI 120000001000 120000001028      9.75    9.75   9.70    01 34  0.200        00                                        0 0.40",
    ]

    def test01(self):
        "vertices A and B at same coordinates, B is moved north-east"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(
            "\n".join(self.ticket_test)
        )

        tests = [
            (obj_list[i].toSufHyd().strip() == self.ticket_test[i]) for i in range(5)
        ]
        self.assertEqual(tests, [True, False, True, True, True])
        self.assertEqual(
            obj_list[1].toSufHyd().strip(),
            "*KNP 12000000290F                 232221001  556283001   10.75  0   300     0.800        00    8.75                                 0",
        )

    def test06(self):
        "vertices A and B at same coordinates, causes one generic WARNING"
        handler.flush()
        HydroObjectFactory.hydroObjectListFromSUFHYD("\n".join(self.ticket_test))
        expect = "found coinciding points"
        records = [i for i in handler.content if i.endswith(expect)]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].split("|", 1)[1], "WARNING|found coinciding points")

    def test07(self):
        "vertices A and B at same coordinates, each modified object is logged as INFO"
        handler.flush()
        HydroObjectFactory.hydroObjectListFromSUFHYD("\n".join(self.ticket_test))
        self.assertEqual(
            handler.content[-1].split("|", 1)[1],
            "INFO|*KNP 12_000000290F was moved from (232221000, 556283000) to (232221001, 556283001)",
        )

    def test11(self):
        "edge from A to A causes WARNING"
        handler.flush()
        ticket_test = self.ticket_test + [
            "*LEI 120000001028 120000001028      9.75    9.75   9.70    01 34  0.200        00                                        0 0.40"
        ]
        HydroObjectFactory.hydroObjectListFromSUFHYD("\n".join(ticket_test))
        self.assertEqual(
            handler.content[-1].split("|", 1)[1],
            "WARNING|edge object *LEI goes from and to 12_0000001028",
        )


class GlueAreaAndLocation(unittest.TestCase):
    ticket_test = [
        "*KNP 12         8                 232221000  556283000   10.65  0   300     0.800        00    9.45                                 0",
        "*KNP  1        28                 232168700  556210600   10.75  0   300     0.800        00    9.75                                 0",
    ]

    def test01(self):
        "avoid ide clash. e.g.: (geb:1, knp:28)/(geb:12, knp:8)"
        handler.flush()
        ticket_test = self.ticket_test
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD("\n".join(ticket_test))
        self.assertEqual(len(obj_list), 2)
        self.assertNotEqual(
            obj_list[0].get_start_pointId(), obj_list[1].get_start_pointId()
        )


class Bug02713(object):  # (unittest.TestCase):
    """TODO: this test is not yet working, so it's not included"""

    ticket_test = """\
*KNP   20                         232221000  556283000
*KNP   20.2                       232222000  556282000
*LEI   20           20.2\000      1   -4.87   -4.87  22.05 01 00     0.300        00                                        0 3.00\000\001\xFF
"""

    def test01(self):
        "bug02713 - test as of ticket"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        mockXsdFile = MockWriter()
        mockGmlFile = MockWriter()
        HydroObjectFactory.propagateGeometries(obj_list)
        HydroObjectFactory.writeGml(obj_list, mockXsdFile, mockGmlFile)
        self.assertEqual([], mockGmlFile.buffer)


class Bug01741(unittest.TestCase):
    ticket_test = """\
*LEI 010000003092   0000003073      9.22    9.18  10.45 00                        3<                                     0
*KNP 010000003092                 234338800  558899000   10.20  0   300                                                             0
*KNP 010000003073                 234343200  558908400   10.16  0   300                                                             0
*PRO 3<  2   9.220  0.000  0.500  0.500  10.220  1.500  3.328  2.500
*PRO 01  5   0.000  0.000 23.950 23.950   1.300 32.435 27.230 25.950   2.500 65.381 31.080 28.960   2.600 68.403 33.608 31.480   2.800 74.731 34.120 31.800
*PRO 8j  2                                0.000  0.000  0.000  0.000   0.830  1.120  3.169  2.700
*PRO 8j  2   0.000  0.000  0.000  0.000   0.830  1.120  3.169  2.700
"""
    fake_profile = "*PRO"

    def test01(self):
        "bug01741 - reading *PRO with n points gives n points (not n-1)."
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        HydroObjectFactory.propagateGeometries(obj_list)
        obj = obj_list[3]
        self.assertEqual(obj.ide_rec, "*PRO")
        self.assertEqual(obj.pro_num, "3<")
        self.assertEqual(obj.pro_com, 2)
        self.assertEqual(obj.pro_nv_000, 9.22)
        self.assertEqual(obj.pro_no_000, 0.0)
        self.assertEqual(obj.pro_hs_000, 0.5)
        self.assertEqual(obj.pro_br_000, 0.5)
        self.assertEqual(obj.pro_nv_001, 10.22)
        self.assertEqual(obj.pro_no_001, 1.5)
        self.assertEqual(obj.pro_hs_001, 3.328)
        self.assertEqual(obj.pro_br_001, 2.5)

        self.assertEqual(obj.toSufHyd().strip(), self.ticket_test.split("\n")[3])
        obj = obj_list[4]
        self.assertEqual(obj.toSufHyd().strip(), self.ticket_test.split("\n")[4])

    def test02(self):
        "bug2069 - leading zero fields should be skipped (data shifted to the left)."
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        HydroObjectFactory.propagateGeometries(obj_list)
        obj = obj_list[5]
        self.assertEqual(obj.toSufHyd().strip(), self.ticket_test.split("\n")[6])

    def test03(self):
        "bug01741 reopened - fake data should not crash the tool."
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.fake_profile)
        HydroObjectFactory.propagateGeometries(obj_list)
        obj = obj_list[0]
        self.assertEqual(obj.toSufHyd().strip(), self.fake_profile)


class GreenBookDefinition(unittest.TestCase):
    ticket_test = """\
*LEI 010000003092   0000003073      9.22    9.18  10.45 00                        3<                                     0
*KNP 010000003092                 234338800  558899000   10.20  0   300                                                             0
*KNP 010000003073                 234343200  558908400   10.16  0   300                                                             0
*PRO 3<  2   9.220  0.000  0.500  0.500  10.220  1.500  3.328  2.500
*GEM 010000003073                            2   33.33   14.26   13.91                   66.67   14.36   13.92
"""

    def test01(self):
        "greenBookDef returns green book compliant definition"

        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        HydroObjectFactory.propagateGeometries(obj_list)
        target = [
            [
                "ide_rec | A 4 | 1-4",
                "ide_geb | A 3 | 5-7",
                "ide_kn1 | A 10 | 8-17",
                "ide_gb2 | A 3 | 18-20",
                "ide_kn2 | A 10 | 21-30",
                "num_mvb | N 2 | 31-32",
                "bob_kn1 | N 8.2 | 33-40",
                "bob_kn2 | N 8.2 | 41-48",
                "lei_len | N 7.2 | 49-55",
                "lei_typ | A 2 | 57-58",
                "pro_mat | A 2 | 60-61",
                "mat_sdr | N 3 | 62-64",
                "pro_bre | N 7.3 | 65-71",
                "pro_hgt | N 7.3 | 72-78",
                "pro_vrm | A 2 | 80-81",
                "pro_num | A 3 | 82-84",
                "afv_een | A 2 | 86-87",
                "afv_hel | N 9.2 | 88-96",
                "afv_vla | N 9.2 | 97-105",
                "afv_vlu | N 9.2 | 106-114",
                "aan_won | N 4 | 115-118",
                "aan_inw | N 4 | 119-122",
                "pro_knw | N 5.2 | 123-127",
                "str_rch | A 2 | 129-130",
                "inv_kn1 | N 4.2 | 131-134",
                "uit_kn1 | N 4.2 | 135-138",
                "inv_kn2 | N 4.2 | 139-142",
                "uit_kn2 | N 4.2 | 143-146",
                "qdh_num | A 2 | 148-149",
                "qdh_niv | N 8.2 | 150-157",
                "nsh_frt | N 2 | 160-161",
                "nsh_frv | N 9.5 | 165-173",
                "dwa_def | A 40 | 175-214",
                "nsh_upt | N 2 | 216-217",
                "nsh_upn | A 40 | 220-259",
            ],
            [
                "ide_rec | A 4 | 1-4",
                "ide_geb | A 3 | 5-7",
                "ide_knp | A 10 | 8-17",
                "knp_xco | N 11 | 33-43",
                "knp_yco | N 11 | 44-54",
                "mvd_niv | N 8.2 | 55-62",
                "mvd_sch | A 2 | 64-65",
                "wos_opp | N 6 | 66-71",
                "pro_mat | A 2 | 73-74",
                "knp_bre | N 7.3 | 75-81",
                "knp_len | N 7.3 | 82-88",
                "knp_vrm | A 2 | 90-91",
                "knp_bok | N 8.2 | 92-99",
                "afv_hel | N 6 | 100-105",
                "afv_vla | N 6 | 106-111",
                "afv_vlu | N 6 | 112-117",
                "loz_con | N 8.2 | 118-125",
                "aan_won | N 4 | 126-129",
                "aan_inw | N 4 | 130-133",
                "dwa_def | A 40 | 134-173",
            ],
            [
                "ide_rec | A 4 | 1-4",
                "ide_geb | A 3 | 5-7",
                "ide_knp | A 10 | 8-17",
                "knp_xco | N 11 | 33-43",
                "knp_yco | N 11 | 44-54",
                "mvd_niv | N 8.2 | 55-62",
                "mvd_sch | A 2 | 64-65",
                "wos_opp | N 6 | 66-71",
                "pro_mat | A 2 | 73-74",
                "knp_bre | N 7.3 | 75-81",
                "knp_len | N 7.3 | 82-88",
                "knp_vrm | A 2 | 90-91",
                "knp_bok | N 8.2 | 92-99",
                "afv_hel | N 6 | 100-105",
                "afv_vla | N 6 | 106-111",
                "afv_vlu | N 6 | 112-117",
                "loz_con | N 8.2 | 118-125",
                "aan_won | N 4 | 126-129",
                "aan_inw | N 4 | 130-133",
                "dwa_def | A 40 | 134-173",
            ],
            [
                "ide_rec | A 4 | 1-4",
                "pro_num | A 3 | 5-7",
                "pro_com | N 3 | 8-10",
                "pro_nv_000 | N 8.3 | 11-18",
                "pro_no_000 | N 7.3 | 19-25",
                "pro_hs_000 | N 7.3 | 26-32",
                "pro_br_000 | N 7.3 | 33-39",
                "pro_nv_001 | N 8.3 | 40-47",
                "pro_no_001 | N 7.3 | 48-54",
                "pro_hs_001 | N 7.3 | 55-61",
                "pro_br_001 | N 7.3 | 62-68",
                "pro_nv_002 | N 8.3 | 69-76",
                "pro_no_002 | N 7.3 | 77-83",
                "pro_hs_002 | N 7.3 | 84-90",
                "pro_br_002 | N 7.3 | 91-97",
                "pro_nv_003 | N 8.3 | 98-105",
                "pro_no_003 | N 7.3 | 106-112",
                "pro_hs_003 | N 7.3 | 113-119",
                "pro_br_003 | N 7.3 | 120-126",
                "pro_nv_004 | N 8.3 | 127-134",
                "pro_no_004 | N 7.3 | 135-141",
                "pro_hs_004 | N 7.3 | 142-148",
                "pro_br_004 | N 7.3 | 149-155",
                "pro_nv_005 | N 8.3 | 156-163",
                "pro_no_005 | N 7.3 | 164-170",
                "pro_hs_005 | N 7.3 | 171-177",
                "pro_br_005 | N 7.3 | 178-184",
                "pro_nv_006 | N 8.3 | 185-192",
                "pro_no_006 | N 7.3 | 193-199",
                "pro_hs_006 | N 7.3 | 200-206",
                "pro_br_006 | N 7.3 | 207-213",
                "pro_nv_007 | N 8.3 | 214-221",
                "pro_no_007 | N 7.3 | 222-228",
                "pro_hs_007 | N 7.3 | 229-235",
                "pro_br_007 | N 7.3 | 236-242",
                "pro_nv_008 | N 8.3 | 243-250",
                "pro_no_008 | N 7.3 | 251-257",
                "pro_hs_008 | N 7.3 | 258-264",
                "pro_br_008 | N 7.3 | 265-271",
                "pro_nv_009 | N 8.3 | 272-279",
                "pro_no_009 | N 7.3 | 280-286",
                "pro_hs_009 | N 7.3 | 287-293",
                "pro_br_009 | N 7.3 | 294-300",
                "pro_nv_010 | N 8.3 | 301-308",
                "pro_no_010 | N 7.3 | 309-315",
                "pro_hs_010 | N 7.3 | 316-322",
                "pro_br_010 | N 7.3 | 323-329",
                "pro_nv_011 | N 8.3 | 330-337",
                "pro_no_011 | N 7.3 | 338-344",
                "pro_hs_011 | N 7.3 | 345-351",
                "pro_br_011 | N 7.3 | 352-358",
                "pro_nv_012 | N 8.3 | 359-366",
                "pro_no_012 | N 7.3 | 367-373",
                "pro_hs_012 | N 7.3 | 374-380",
                "pro_br_012 | N 7.3 | 381-387",
                "pro_nv_013 | N 8.3 | 388-395",
                "pro_no_013 | N 7.3 | 396-402",
                "pro_hs_013 | N 7.3 | 403-409",
                "pro_br_013 | N 7.3 | 410-416",
                "pro_nv_014 | N 8.3 | 417-424",
                "pro_no_014 | N 7.3 | 425-431",
                "pro_hs_014 | N 7.3 | 432-438",
                "pro_br_014 | N 7.3 | 439-445",
                "pro_nv_015 | N 8.3 | 446-453",
                "pro_no_015 | N 7.3 | 454-460",
                "pro_hs_015 | N 7.3 | 461-467",
                "pro_br_015 | N 7.3 | 468-474",
                "pro_nv_016 | N 8.3 | 475-482",
                "pro_no_016 | N 7.3 | 483-489",
                "pro_hs_016 | N 7.3 | 490-496",
                "pro_br_016 | N 7.3 | 497-503",
                "pro_nv_017 | N 8.3 | 504-511",
                "pro_no_017 | N 7.3 | 512-518",
                "pro_hs_017 | N 7.3 | 519-525",
                "pro_br_017 | N 7.3 | 526-532",
                "pro_nv_018 | N 8.3 | 533-540",
                "pro_no_018 | N 7.3 | 541-547",
                "pro_hs_018 | N 7.3 | 548-554",
                "pro_br_018 | N 7.3 | 555-561",
                "pro_nv_019 | N 8.3 | 562-569",
                "pro_no_019 | N 7.3 | 570-576",
                "pro_hs_019 | N 7.3 | 577-583",
                "pro_br_019 | N 7.3 | 584-590",
                "pro_nv_020 | N 8.3 | 591-598",
                "pro_no_020 | N 7.3 | 599-605",
                "pro_hs_020 | N 7.3 | 606-612",
                "pro_br_020 | N 7.3 | 613-619",
                "pro_nv_021 | N 8.3 | 620-627",
                "pro_no_021 | N 7.3 | 628-634",
                "pro_hs_021 | N 7.3 | 635-641",
                "pro_br_021 | N 7.3 | 642-648",
                "pro_nv_022 | N 8.3 | 649-656",
                "pro_no_022 | N 7.3 | 657-663",
                "pro_hs_022 | N 7.3 | 664-670",
                "pro_br_022 | N 7.3 | 671-677",
                "pro_nv_023 | N 8.3 | 678-685",
                "pro_no_023 | N 7.3 | 686-692",
                "pro_hs_023 | N 7.3 | 693-699",
                "pro_br_023 | N 7.3 | 700-706",
                "pro_nv_024 | N 8.3 | 707-714",
                "pro_no_024 | N 7.3 | 715-721",
                "pro_hs_024 | N 7.3 | 722-728",
                "pro_br_024 | N 7.3 | 729-735",
                "pro_nv_025 | N 8.3 | 736-743",
                "pro_no_025 | N 7.3 | 744-750",
                "pro_hs_025 | N 7.3 | 751-757",
                "pro_br_025 | N 7.3 | 758-764",
                "pro_nv_026 | N 8.3 | 765-772",
                "pro_no_026 | N 7.3 | 773-779",
                "pro_hs_026 | N 7.3 | 780-786",
                "pro_br_026 | N 7.3 | 787-793",
                "pro_nv_027 | N 8.3 | 794-801",
                "pro_no_027 | N 7.3 | 802-808",
                "pro_hs_027 | N 7.3 | 809-815",
                "pro_br_027 | N 7.3 | 816-822",
                "pro_nv_028 | N 8.3 | 823-830",
                "pro_no_028 | N 7.3 | 831-837",
                "pro_hs_028 | N 7.3 | 838-844",
                "pro_br_028 | N 7.3 | 845-851",
                "pro_nv_029 | N 8.3 | 852-859",
                "pro_no_029 | N 7.3 | 860-866",
                "pro_hs_029 | N 7.3 | 867-873",
                "pro_br_029 | N 7.3 | 874-880",
                "pro_nv_030 | N 8.3 | 881-888",
                "pro_no_030 | N 7.3 | 889-895",
                "pro_hs_030 | N 7.3 | 896-902",
                "pro_br_030 | N 7.3 | 903-909",
                "pro_nv_031 | N 8.3 | 910-917",
                "pro_no_031 | N 7.3 | 918-924",
                "pro_hs_031 | N 7.3 | 925-931",
                "pro_br_031 | N 7.3 | 932-938",
                "pro_nv_032 | N 8.3 | 939-946",
                "pro_no_032 | N 7.3 | 947-953",
                "pro_hs_032 | N 7.3 | 954-960",
                "pro_br_032 | N 7.3 | 961-967",
                "pro_nv_033 | N 8.3 | 968-975",
                "pro_no_033 | N 7.3 | 976-982",
                "pro_hs_033 | N 7.3 | 983-989",
                "pro_br_033 | N 7.3 | 990-996",
                "pro_nv_034 | N 8.3 | 997-1004",
                "pro_no_034 | N 7.3 | 1005-1011",
                "pro_hs_034 | N 7.3 | 1012-1018",
                "pro_br_034 | N 7.3 | 1019-1025",
                "pro_nv_035 | N 8.3 | 1026-1033",
                "pro_no_035 | N 7.3 | 1034-1040",
                "pro_hs_035 | N 7.3 | 1041-1047",
                "pro_br_035 | N 7.3 | 1048-1054",
                "pro_nv_036 | N 8.3 | 1055-1062",
                "pro_no_036 | N 7.3 | 1063-1069",
                "pro_hs_036 | N 7.3 | 1070-1076",
                "pro_br_036 | N 7.3 | 1077-1083",
                "pro_nv_037 | N 8.3 | 1084-1091",
                "pro_no_037 | N 7.3 | 1092-1098",
                "pro_hs_037 | N 7.3 | 1099-1105",
                "pro_br_037 | N 7.3 | 1106-1112",
                "pro_nv_038 | N 8.3 | 1113-1120",
                "pro_no_038 | N 7.3 | 1121-1127",
                "pro_hs_038 | N 7.3 | 1128-1134",
                "pro_br_038 | N 7.3 | 1135-1141",
                "pro_nv_039 | N 8.3 | 1142-1149",
                "pro_no_039 | N 7.3 | 1150-1156",
                "pro_hs_039 | N 7.3 | 1157-1163",
                "pro_br_039 | N 7.3 | 1164-1170",
                "pro_nv_040 | N 8.3 | 1171-1178",
                "pro_no_040 | N 7.3 | 1179-1185",
                "pro_hs_040 | N 7.3 | 1186-1192",
                "pro_br_040 | N 7.3 | 1193-1199",
                "pro_nv_041 | N 8.3 | 1200-1207",
                "pro_no_041 | N 7.3 | 1208-1214",
                "pro_hs_041 | N 7.3 | 1215-1221",
                "pro_br_041 | N 7.3 | 1222-1228",
                "pro_nv_042 | N 8.3 | 1229-1236",
                "pro_no_042 | N 7.3 | 1237-1243",
                "pro_hs_042 | N 7.3 | 1244-1250",
                "pro_br_042 | N 7.3 | 1251-1257",
                "pro_nv_043 | N 8.3 | 1258-1265",
                "pro_no_043 | N 7.3 | 1266-1272",
                "pro_hs_043 | N 7.3 | 1273-1279",
                "pro_br_043 | N 7.3 | 1280-1286",
                "pro_nv_044 | N 8.3 | 1287-1294",
                "pro_no_044 | N 7.3 | 1295-1301",
                "pro_hs_044 | N 7.3 | 1302-1308",
                "pro_br_044 | N 7.3 | 1309-1315",
                "pro_nv_045 | N 8.3 | 1316-1323",
                "pro_no_045 | N 7.3 | 1324-1330",
                "pro_hs_045 | N 7.3 | 1331-1337",
                "pro_br_045 | N 7.3 | 1338-1344",
                "pro_nv_046 | N 8.3 | 1345-1352",
                "pro_no_046 | N 7.3 | 1353-1359",
                "pro_hs_046 | N 7.3 | 1360-1366",
                "pro_br_046 | N 7.3 | 1367-1373",
                "pro_nv_047 | N 8.3 | 1374-1381",
                "pro_no_047 | N 7.3 | 1382-1388",
                "pro_hs_047 | N 7.3 | 1389-1395",
                "pro_br_047 | N 7.3 | 1396-1402",
                "pro_nv_048 | N 8.3 | 1403-1410",
                "pro_no_048 | N 7.3 | 1411-1417",
                "pro_hs_048 | N 7.3 | 1418-1424",
                "pro_br_048 | N 7.3 | 1425-1431",
                "pro_nv_049 | N 8.3 | 1432-1439",
                "pro_no_049 | N 7.3 | 1440-1446",
                "pro_hs_049 | N 7.3 | 1447-1453",
                "pro_br_049 | N 7.3 | 1454-1460",
            ],
            [
                "ide_rec | A 4 | 1-4",
                "ide_gb1 | A 3 | 5-7",
                "ide_kn1 | A 10 | 8-17",
                "ide_gb2 | A 3 | 18-20",
                "num_mvb | N 2 | 31-32",
                "qdh_num | A 2 | 34-35",
                "qdh_niv | N 8.2 | 36-43",
                "pmp_com | N 3 | 44-46",
                "pmp_pc1 | N 8.2 | 47-54",
                "pmp_an1 | N 8.2 | 55-62",
                "pmp_af1 | N 8.2 | 63-70",
                "rel_an1 | N 8.2 | 71-78",
                "rel_af1 | N 8.2 | 79-86",
                "pmp_pc2 | N 8.2 | 87-94",
                "pmp_an2 | N 8.2 | 95-102",
                "pmp_af2 | N 8.2 | 103-110",
                "rel_an2 | N 8.2 | 111-118",
                "rel_af2 | N 8.2 | 119-126",
                "pmp_pc3 | N 8.2 | 127-134",
                "pmp_an3 | N 8.2 | 135-142",
                "pmp_af3 | N 8.2 | 143-150",
                "rel_an3 | N 8.2 | 151-158",
                "rel_af3 | N 8.2 | 159-166",
                "pmp_pc4 | N 8.2 | 167-174",
                "pmp_an4 | N 8.2 | 175-182",
                "pmp_af4 | N 8.2 | 183-190",
                "rel_an4 | N 8.2 | 191-198",
                "rel_af4 | N 8.2 | 199-206",
                "pmp_pc5 | N 8.2 | 207-214",
                "pmp_an5 | N 8.2 | 215-222",
                "pmp_af5 | N 8.2 | 223-230",
                "rel_an5 | N 8.2 | 231-238",
                "rel_af5 | N 8.2 | 239-246",
                "pmp_pc6 | N 8.2 | 247-254",
                "pmp_an6 | N 8.2 | 255-262",
                "pmp_af6 | N 8.2 | 263-270",
                "rel_an6 | N 8.2 | 271-278",
                "rel_af6 | N 8.2 | 279-286",
                "pmp_pc7 | N 8.2 | 287-294",
                "pmp_an7 | N 8.2 | 295-302",
                "pmp_af7 | N 8.2 | 303-310",
                "rel_an7 | N 8.2 | 311-318",
                "rel_af7 | N 8.2 | 319-326",
                "pmp_pc8 | N 8.2 | 327-334",
                "pmp_an8 | N 8.2 | 335-342",
                "pmp_af8 | N 8.2 | 343-350",
                "rel_an8 | N 8.2 | 351-358",
                "rel_af8 | N 8.2 | 359-366",
            ],
        ]
        current = [obj.greenBookDef() for obj in obj_list]
        for current_item, target_item in map(None, current, target):
            for current_item_item, target_item_item in map(
                None, current_item, target_item
            ):
                self.assertEqual(current_item_item, target_item_item)


class NetworkXIntegration(unittest.TestCase):
    ticket_test = """\
*LEI 010000003092   0000003073      9.22    9.18  10.45 00                        3<                                     0
*KNP 010000003092                 234338800  558899000   10.20  0   300                                                             0
*KNP 010000003073                 234343200  558908400   10.16  0   300                                                             0
*PRO 3<  2   9.220  0.000  0.500  0.500  10.220  1.500  3.328  2.500
*GEM 010000003073                            2   33.33   14.26   13.91                   66.67   14.36   13.92
"""

    def test010(self):
        "node represents itself in useful format for add_nodes_from"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)

        ids = ["", "01_0000003092", "01_0000003073", "", "01_0000003073"]
        for i in [1, 2, 4]:
            current = obj_list[i].toNxTuple()
            self.assertEqual((ids[i],), current[:1])
            common_keys = set(current[1].keys()).intersection(
                list(obj_list[i].fields.keys())
            )
            self.assertEqual(set(obj_list[i].fields.keys()), common_keys)

    def test015(self):
        "toNxTuple reports 'x' and 'y' fields only for *KNP objects"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)

        for i in range(5):
            obj = obj_list[i]
            if not hasattr(obj_list[3], "toNxTuple"):
                continue
            current = obj.toNxTuple()
            if current[-1]["ide_rec"] == "*KNP":
                self.assertTrue("x" in list(current[-1].keys()))
                self.assertTrue("y" in list(current[-1].keys()))
            else:
                self.assertFalse("x" in list(current[-1].keys()))
                self.assertFalse("y" in list(current[-1].keys()))

    def test020(self):
        "vertex represents itself in useful format for add_edges_from"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        current = obj_list[0].toNxTuple()
        self.assertEqual(("01_0000003092", "01_0000003073"), current[:2])
        self.assertEqual(obj_list[0].fields, current[2])

    def test030(self):
        "toNxTuple on neither node nor vertex objects raises exception"
        obj_list = HydroObjectFactory.hydroObjectListFromSUFHYD(self.ticket_test)
        self.assertFalse(hasattr(obj_list[3], "toNxTuple"))


class DoctestRunner(unittest.TestCase):
    def test0000(self):
        import doctest

        doctest.testmod(name=__name__[:-6])
