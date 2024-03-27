<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis readOnly="0" version="3.4.12-Madeira" hasScaleBasedVisibilityFlag="0" minScale="1e+08" styleCategories="AllStyleCategories" labelsEnabled="0" simplifyMaxScale="1" simplifyLocal="1" maxScale="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyAlgorithm="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 symbollevels="1" enableorderby="0" type="RuleRenderer" forceraster="0">
    <rules key="{0ec33efc-5a71-4c69-b327-54c4b6f47021}">
      <rule key="{8ac2bd7f-45f2-4e73-b7bd-be516cf4f33d}" symbol="0" filter="ts_max_below_thres_1_0 >10 OR  ts_max_below_thres_3_0 > 50 or ts_max_below_thres_5_0 > 80"/>
      <rule key="{83204a3a-88e8-4e7a-855c-18c555939e4e}" symbol="1" filter="ELSE"/>
    </rules>
    <symbols>
      <symbol alpha="1" force_rhr="0" name="0" type="line" clip_to_extent="1">
        <layer locked="0" pass="1" enabled="1" class="SimpleLine">
          <prop k="capstyle" v="round"/>
          <prop k="customdash" v="5;2"/>
          <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="customdash_unit" v="MM"/>
          <prop k="draw_inside_polygon" v="0"/>
          <prop k="joinstyle" v="round"/>
          <prop k="line_color" v="227,26,28,255"/>
          <prop k="line_style" v="solid"/>
          <prop k="line_width" v="1.86"/>
          <prop k="line_width_unit" v="MM"/>
          <prop k="offset" v="0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="ring_filter" v="0"/>
          <prop k="use_custom_dash" v="0"/>
          <prop k="width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <effect enabled="1" type="effectStack">
            <effect type="dropShadow">
              <prop k="blend_mode" v="13"/>
              <prop k="blur_level" v="2.645"/>
              <prop k="blur_unit" v="MM"/>
              <prop k="blur_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="color" v="0,0,0,255"/>
              <prop k="draw_mode" v="2"/>
              <prop k="enabled" v="0"/>
              <prop k="offset_angle" v="135"/>
              <prop k="offset_distance" v="2"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="offset_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="opacity" v="1"/>
            </effect>
            <effect type="outerGlow">
              <prop k="blend_mode" v="0"/>
              <prop k="blur_level" v="0.7935"/>
              <prop k="blur_unit" v="MM"/>
              <prop k="blur_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="color1" v="0,0,255,255"/>
              <prop k="color2" v="0,255,0,255"/>
              <prop k="color_type" v="0"/>
              <prop k="discrete" v="0"/>
              <prop k="draw_mode" v="2"/>
              <prop k="enabled" v="1"/>
              <prop k="opacity" v="0.5"/>
              <prop k="rampType" v="gradient"/>
              <prop k="single_color" v="239,41,41,255"/>
              <prop k="spread" v="2"/>
              <prop k="spread_unit" v="MM"/>
              <prop k="spread_unit_scale" v="3x:0,0,0,0,0,0"/>
            </effect>
            <effect type="drawSource">
              <prop k="blend_mode" v="0"/>
              <prop k="draw_mode" v="2"/>
              <prop k="enabled" v="1"/>
              <prop k="opacity" v="1"/>
            </effect>
            <effect type="innerShadow">
              <prop k="blend_mode" v="13"/>
              <prop k="blur_level" v="2.645"/>
              <prop k="blur_unit" v="MM"/>
              <prop k="blur_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="color" v="0,0,0,255"/>
              <prop k="draw_mode" v="2"/>
              <prop k="enabled" v="1"/>
              <prop k="offset_angle" v="135"/>
              <prop k="offset_distance" v="2"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="offset_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="opacity" v="0.146"/>
            </effect>
            <effect type="innerGlow">
              <prop k="blend_mode" v="0"/>
              <prop k="blur_level" v="0.7935"/>
              <prop k="blur_unit" v="MM"/>
              <prop k="blur_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="color1" v="0,0,255,255"/>
              <prop k="color2" v="0,255,0,255"/>
              <prop k="color_type" v="0"/>
              <prop k="discrete" v="0"/>
              <prop k="draw_mode" v="2"/>
              <prop k="enabled" v="0"/>
              <prop k="opacity" v="0.386"/>
              <prop k="rampType" v="gradient"/>
              <prop k="single_color" v="255,255,255,255"/>
              <prop k="spread" v="2"/>
              <prop k="spread_unit" v="MM"/>
              <prop k="spread_unit_scale" v="3x:0,0,0,0,0,0"/>
            </effect>
          </effect>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" force_rhr="0" name="1" type="line" clip_to_extent="1">
        <layer locked="0" pass="0" enabled="1" class="SimpleLine">
          <prop k="capstyle" v="square"/>
          <prop k="customdash" v="5;2"/>
          <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="customdash_unit" v="MM"/>
          <prop k="draw_inside_polygon" v="0"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="line_color" v="49,45,105,255"/>
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <customproperties>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer attributeLegend="1" diagramType="Histogram">
    <DiagramCategory lineSizeType="MM" sizeScale="3x:0,0,0,0,0,0" scaleDependency="Area" width="15" rotationOffset="270" height="15" lineSizeScale="3x:0,0,0,0,0,0" labelPlacementMethod="XHeight" penWidth="0" minimumSize="0" minScaleDenominator="0" enabled="0" opacity="1" scaleBasedVisibility="0" backgroundAlpha="255" sizeType="MM" diagramOrientation="Up" backgroundColor="#ffffff" penAlpha="255" maxScaleDenominator="1e+08" penColor="#000000" barWidth="5">
      <fontProperties style="" description="MS Shell Dlg 2,7.8,-1,5,50,0,0,0,0,0"/>
      <attribute field="" color="#000000" label=""/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings obstacle="0" priority="0" dist="0" linePlacementFlags="18" placement="2" zIndex="0" showAll="1">
    <properties>
      <Option type="Map">
        <Option name="name" type="QString" value=""/>
        <Option name="properties"/>
        <Option name="type" type="QString" value="collection"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="id">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="content_type">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="spatialite_id">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="kcu">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="kcu_description">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ts_max_below_thres_1_0">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ts_max_below_thres_3_0">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ts_max_below_thres_5_0">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="id" name="" index="0"/>
    <alias field="content_type" name="" index="1"/>
    <alias field="spatialite_id" name="" index="2"/>
    <alias field="kcu" name="" index="3"/>
    <alias field="kcu_description" name="" index="4"/>
    <alias field="ts_max_below_thres_1_0" name="" index="5"/>
    <alias field="ts_max_below_thres_3_0" name="" index="6"/>
    <alias field="ts_max_below_thres_5_0" name="" index="7"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="id" expression="" applyOnUpdate="0"/>
    <default field="content_type" expression="" applyOnUpdate="0"/>
    <default field="spatialite_id" expression="" applyOnUpdate="0"/>
    <default field="kcu" expression="" applyOnUpdate="0"/>
    <default field="kcu_description" expression="" applyOnUpdate="0"/>
    <default field="ts_max_below_thres_1_0" expression="" applyOnUpdate="0"/>
    <default field="ts_max_below_thres_3_0" expression="" applyOnUpdate="0"/>
    <default field="ts_max_below_thres_5_0" expression="" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint field="id" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="content_type" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="spatialite_id" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="kcu" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="kcu_description" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="ts_max_below_thres_1_0" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="ts_max_below_thres_3_0" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
    <constraint field="ts_max_below_thres_5_0" notnull_strength="0" unique_strength="0" constraints="0" exp_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="id" desc="" exp=""/>
    <constraint field="content_type" desc="" exp=""/>
    <constraint field="spatialite_id" desc="" exp=""/>
    <constraint field="kcu" desc="" exp=""/>
    <constraint field="kcu_description" desc="" exp=""/>
    <constraint field="ts_max_below_thres_1_0" desc="" exp=""/>
    <constraint field="ts_max_below_thres_3_0" desc="" exp=""/>
    <constraint field="ts_max_below_thres_5_0" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" sortExpression="" actionWidgetStyle="dropDown">
    <columns>
      <column width="-1" name="id" hidden="0" type="field"/>
      <column width="-1" name="content_type" hidden="0" type="field"/>
      <column width="-1" name="spatialite_id" hidden="0" type="field"/>
      <column width="-1" hidden="1" type="actions"/>
      <column width="-1" name="kcu" hidden="0" type="field"/>
      <column width="-1" name="kcu_description" hidden="0" type="field"/>
      <column width="-1" name="ts_max_below_thres_1_0" hidden="0" type="field"/>
      <column width="-1" name="ts_max_below_thres_3_0" hidden="0" type="field"/>
      <column width="-1" name="ts_max_below_thres_5_0" hidden="0" type="field"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
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
    <field name="content_type" editable="1"/>
    <field name="id" editable="1"/>
    <field name="kcu" editable="1"/>
    <field name="kcu_description" editable="1"/>
    <field name="q_pos_sum" editable="1"/>
    <field name="spatialite_id" editable="1"/>
    <field name="ts_max_below_thres_1_0" editable="1"/>
    <field name="ts_max_below_thres_3_0" editable="1"/>
    <field name="ts_max_below_thres_5_0" editable="1"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="content_type"/>
    <field labelOnTop="0" name="id"/>
    <field labelOnTop="0" name="kcu"/>
    <field labelOnTop="0" name="kcu_description"/>
    <field labelOnTop="0" name="q_pos_sum"/>
    <field labelOnTop="0" name="spatialite_id"/>
    <field labelOnTop="0" name="ts_max_below_thres_1_0"/>
    <field labelOnTop="0" name="ts_max_below_thres_3_0"/>
    <field labelOnTop="0" name="ts_max_below_thres_5_0"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>id</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>1</layerGeometryType>
</qgis>
