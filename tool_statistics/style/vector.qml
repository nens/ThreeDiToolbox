<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.14.0-Pi" labelsEnabled="0" simplifyAlgorithm="0" minScale="100000000" simplifyDrawingHints="0" hasScaleBasedVisibilityFlag="0" readOnly="0" simplifyDrawingTol="1" simplifyMaxScale="1" styleCategories="AllStyleCategories" simplifyLocal="1" maxScale="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <temporal endExpression="" accumulate="0" enabled="0" mode="0" durationField="" endField="" startExpression="" startField="" fixedDuration="0" durationUnit="min">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <renderer-v2 type="graduatedSymbol" forceraster="0" attr="sqrt(&quot;q_out_x_sum&quot; * &quot;q_out_x_sum&quot; + &quot;q_out_y_sum&quot; * &quot;q_out_y_sum&quot;)" enableorderby="0" symbollevels="0" graduatedMethod="GraduatedColor">
    <ranges>
      <range render="true" upper="0.991020438114674" label="0 - 0.991" lower="0.000000000000000" symbol="0"/>
      <range render="true" upper="1.412345719337464" label="0.991 - 1.4123" lower="0.991020438114674" symbol="1"/>
      <range render="true" upper="1.854538999729660" label="1.4123 - 1.8545" lower="1.412345719337464" symbol="2"/>
      <range render="true" upper="2.676778713089883" label="1.8545 - 2.6768" lower="1.854538999729660" symbol="3"/>
      <range render="true" upper="3.648641277950022" label="2.6768 - 3.6486" lower="2.676778713089883" symbol="4"/>
      <range render="true" upper="5.330184051641331" label="3.6486 - 5.3302" lower="3.648641277950022" symbol="5"/>
      <range render="true" upper="8.287233827564663" label="5.3302 - 8.2872" lower="5.330184051641331" symbol="6"/>
      <range render="true" upper="13.991849153165457" label="8.2872 - 13.9918" lower="8.287233827564663" symbol="7"/>
      <range render="true" upper="29.024281531013909" label="13.9918 - 29.0243" lower="13.991849153165457" symbol="8"/>
      <range render="true" upper="316.541482593017065" label="29.0243 - 316.5415" lower="29.024281531013909" symbol="9"/>
    </ranges>
    <symbols>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="0">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="247,251,255,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="1">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="226,238,249,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="2">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="205,224,242,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="3">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="176,210,232,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="4">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="137,191,221,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="5">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="96,166,210,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="6">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="62,142,196,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="7">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="33,114,182,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="8">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="10,84,158,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="9">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="8,48,107,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <source-symbol>
      <symbol type="marker" alpha="1" clip_to_extent="1" force_rhr="0" name="0">
        <layer enabled="1" class="SvgMarker" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="0,0,0,255"/>
          <prop k="fixedAspectRatio" v="2"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="arrows/Arrow_05.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="degrees(azimuth( make_point( 0,0), make_point( &quot;q_out_x_sum&quot;,  &quot;q_out_y_sum&quot; )))" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="size">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="int" value="1" name="type"/>
                  <Option type="QString" value="" name="val"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </source-symbol>
    <colorramp type="gradient" name="[source]">
      <prop k="color1" v="247,251,255,255"/>
      <prop k="color2" v="8,48,107,255"/>
      <prop k="discrete" v="0"/>
      <prop k="rampType" v="gradient"/>
      <prop k="stops" v="0.13;222,235,247,255:0.26;198,219,239,255:0.39;158,202,225,255:0.52;107,174,214,255:0.65;66,146,198,255:0.78;33,113,181,255:0.9;8,81,156,255"/>
    </colorramp>
    <classificationMethod id="Quantile">
      <symmetricMode enabled="0" astride="0" symmetrypoint="0"/>
      <labelFormat format="%1 - %2" trimtrailingzeroes="1" labelprecision="4"/>
      <parameters>
        <Option/>
      </parameters>
      <extraInformation/>
    </classificationMethod>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <customproperties>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames">
      <value>vfr_metres_to_unit</value>
      <value>vfr_scale</value>
    </property>
    <property key="variableValues">
      <value>1.9349746982808556</value>
      <value>1.0</value>
    </property>
    <property value="" key="vfr_scale_group"/>
    <property value="1" key="vfr_scale_group_factor"/>
    <property value="{&quot;arrowAngleDegrees&quot;: false, &quot;arrowAngleFromNorth&quot;: true, &quot;arrowBorderColor&quot;: &quot;#ff000000&quot;, &quot;arrowBorderWidth&quot;: 0.0, &quot;arrowFillColor&quot;: &quot;#ff000000&quot;, &quot;arrowHeadRelativeLength&quot;: 1.5, &quot;arrowHeadWidth&quot;: 3.0, &quot;arrowMaxRelativeHeadSize&quot;: 0.3, &quot;arrowMode&quot;: &quot;xy&quot;, &quot;arrowShaftWidth&quot;: 0.75, &quot;baseBorderColor&quot;: &quot;#ff000000&quot;, &quot;baseBorderWidth&quot;: 0.0, &quot;baseFillColor&quot;: &quot;#ffff0000&quot;, &quot;baseSize&quot;: 2.0, &quot;drawArrow&quot;: true, &quot;drawEllipse&quot;: true, &quot;drawEllipseAxes&quot;: false, &quot;dxField&quot;: &quot;q_out_x_sum&quot;, &quot;dyField&quot;: &quot;q_out_y_sum&quot;, &quot;ellipseAngleFromNorth&quot;: true, &quot;ellipseBorderColor&quot;: &quot;#ff000000&quot;, &quot;ellipseBorderWidth&quot;: 0.7, &quot;ellipseDegrees&quot;: true, &quot;ellipseFillColor&quot;: &quot;#ff000000&quot;, &quot;ellipseMode&quot;: &quot;axes&quot;, &quot;ellipseScale&quot;: 1.0, &quot;ellipseTickSize&quot;: 2.0, &quot;emaxAzimuthField&quot;: &quot;&quot;, &quot;emaxField&quot;: &quot;&quot;, &quot;eminField&quot;: &quot;&quot;, &quot;fillArrow&quot;: true, &quot;fillBase&quot;: true, &quot;fillEllipse&quot;: false, &quot;scale&quot;: 1.0, &quot;scaleGroup&quot;: &quot;&quot;, &quot;scaleGroupFactor&quot;: 1.0, &quot;scaleIsMetres&quot;: false, &quot;symbolRenderUnit&quot;: &quot;mm&quot;}" key="vfr_settings"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory backgroundAlpha="255" backgroundColor="#ffffff" minScaleDenominator="0" rotationOffset="270" enabled="0" sizeType="MM" labelPlacementMethod="XHeight" width="15" direction="1" lineSizeScale="3x:0,0,0,0,0,0" minimumSize="0" sizeScale="3x:0,0,0,0,0,0" penWidth="0" scaleBasedVisibility="0" lineSizeType="MM" showAxis="0" opacity="1" maxScaleDenominator="1e+08" barWidth="5" penAlpha="255" diagramOrientation="Up" spacing="0" penColor="#000000" spacingUnit="MM" spacingUnitScale="3x:0,0,0,0,0,0" scaleDependency="Area" height="15">
      <fontProperties description="MS Shell Dlg 2,7.8,-1,5,50,0,0,0,0,0" style=""/>
      <attribute field="" label="" color="#000000"/>
      <axisSymbol>
        <symbol type="line" alpha="1" clip_to_extent="1" force_rhr="0" name="">
          <layer enabled="1" class="SimpleLine" pass="0" locked="0">
            <prop k="capstyle" v="square"/>
            <prop k="customdash" v="5;2"/>
            <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <prop k="customdash_unit" v="MM"/>
            <prop k="draw_inside_polygon" v="0"/>
            <prop k="joinstyle" v="bevel"/>
            <prop k="line_color" v="35,35,35,255"/>
            <prop k="line_style" v="solid"/>
            <prop k="line_width" v="0.26"/>
            <prop k="line_width_unit" v="MM"/>
            <prop k="offset" v="0"/>
            <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <prop k="offset_unit" v="MM"/>
            <prop k="ring_filter" v="0"/>
            <prop k="use_custom_dash" v="0"/>
            <prop k="width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <data_defined_properties>
              <Option type="Map">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
            </data_defined_properties>
          </layer>
        </symbol>
      </axisSymbol>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings zIndex="0" priority="0" placement="0" dist="0" showAll="1" obstacle="0" linePlacementFlags="18">
    <properties>
      <Option type="Map">
        <Option type="QString" value="" name="name"/>
        <Option name="properties"/>
        <Option type="QString" value="collection" name="type"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <referencedLayers/>
  <referencingLayers/>
  <fieldConfiguration>
    <field name="q_out_x_sum">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="q_out_y_sum">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias index="0" field="q_out_x_sum" name=""/>
    <alias index="1" field="q_out_y_sum" name=""/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default applyOnUpdate="0" expression="" field="q_out_x_sum"/>
    <default applyOnUpdate="0" expression="" field="q_out_y_sum"/>
  </defaults>
  <constraints>
    <constraint constraints="0" exp_strength="0" unique_strength="0" field="q_out_x_sum" notnull_strength="0"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" field="q_out_y_sum" notnull_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="q_out_x_sum" desc="" exp=""/>
    <constraint field="q_out_y_sum" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" sortExpression="" actionWidgetStyle="dropDown">
    <columns>
      <column type="field" hidden="0" width="-1" name="q_out_x_sum"/>
      <column type="field" hidden="0" width="-1" name="q_out_y_sum"/>
      <column type="actions" hidden="1" width="-1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="id" editable="1"/>
    <field name="node_type" editable="1"/>
    <field name="q_out_x_sum" editable="1"/>
    <field name="q_out_y_sum" editable="1"/>
    <field name="spatialite_id" editable="1"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="id"/>
    <field labelOnTop="0" name="node_type"/>
    <field labelOnTop="0" name="q_out_x_sum"/>
    <field labelOnTop="0" name="q_out_y_sum"/>
    <field labelOnTop="0" name="spatialite_id"/>
  </labelOnTop>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>"id"</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
