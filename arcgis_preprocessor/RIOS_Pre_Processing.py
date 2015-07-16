# ---------------------------------------------------------------------------
# RIOS_Pre_Processing.py
# 
# Coded by Stacie Wolny
# for the Natural Capital Project
#
# Performs the calculations necessary for producing input 
#    to the RIOS 1.0.0 IPA tool
#
# ---------------------------------------------------------------------------



# Import system modules
import sys, string, os, arcgisscripting, time, datetime

# Create the Geoprocessor object
gp = arcgisscripting.create()

# Check out any necessary licenses
gp.CheckOutExtension("spatial")

# Set output handling
gp.OverwriteOutput = 1

# Set to true to enable reporting
verbose = True
cleanup = True

try:
    
    ### Process inputs
    
    try:

        # Make parameters array, and later write input parameter values to an output file
        parameters = []
        now = datetime.datetime.now()
        parameters.append("Date and Time: "+ now.strftime("%Y-%m-%d %H:%M"))

        gp.AddMessage ("\nValidating arguments..." )
        
        # Calculate inputs for the objective of Erosion Control?
        do_erosion = sys.argv[1]
        parameters.append("Calculate for Erosion Control: " + do_erosion)

        # Calculate inputs for the objective of Phosphorus Retention?
        do_nutrient_p = sys.argv[2]
        parameters.append("Calculate for Phosphorus Retention: " + do_nutrient_p)
        
        # Calculate inputs for the objective of Nitrogen Retention?
        do_nutrient_n = sys.argv[3]
        parameters.append("Calculate for Nitrogen Retention: " + do_nutrient_n)
                
        # Calculate inputs for the objective of Flood Mitigation?
        do_flood = sys.argv[4]
        parameters.append("Calculate for Flood Mitigation: " + do_flood)

        # Calculate inputs for the objective of Groundwater Recharge/Baseflow?
        do_gw_bf = sys.argv[5]
        parameters.append("Calculate for Groundwater Recharge/Baseflow: " + do_gw_bf)

        # Directory where output files will be written
        gp.workspace = sys.argv[6]
        parameters.append("Workspace: " + gp.workspace)

        # Land use / land cover raster
        lulc = sys.argv[7]
        parameters.append("Land use/land cover: " + lulc)
        if (lulc != "") and (lulc != string.whitespace) and (lulc != "#"):
            lulc_found = True
        else:
            lulc_found = False

##        # Land use / land cover general class/activities table
##        lulc_general_table = sys.argv[8]
##        parameters.append("Land use general classes/activities table: " + lulc_general_table)
##        if (lulc_general_table != "") and (lulc_general_table != string.whitespace) and (lulc_general_table != "#"):
##            lulc_general_table_found = True
##        else:
##            lulc_general_table_found = False

        # RIOS biophysical coefficient table
        rios_coeff_table = sys.argv[8]
        parameters.append("RIOS biophysical coefficient table: " + rios_coeff_table)
        if (rios_coeff_table != "") and (rios_coeff_table != string.whitespace) and (rios_coeff_table != "#"):
            rios_coeff_table_found = True
        else:
            rios_coeff_table_found = False
        
        # Digital elevation model (DEM) raster
        DEM = sys.argv[9]
        parameters.append("DEM: " + DEM)
        if (DEM != "") and (DEM != string.whitespace) and (DEM != "#"):
            dem_found = True
        else:
            dem_found = False

        # Rainfall erosivity raster
        erosivity = sys.argv[10]
        parameters.append("Rainfall erosivity: " + erosivity)
        if (erosivity != "") and (erosivity != string.whitespace) and (erosivity != "#"):
            erosivity_found = True
        else:
            erosivity_found = False
        
        # Erodibility raster
        erodibility = sys.argv[11]
        parameters.append("Erodibility: " + erodibility)
        if (erodibility != "") and (erodibility != string.whitespace) and (erodibility != "#"):
            erodibility_found = True
        else:
            erodibility_found = False

        # Soil depth raster
        soil_depth = sys.argv[12]
        parameters.append("Soil depth: " + soil_depth)
        if (soil_depth != "") and (soil_depth != string.whitespace) and (soil_depth != "#"):
            soil_depth_found = True
        else:
            soil_depth_found = False
        
        # Precipitation depth for wettest month
        precip_month = sys.argv[13]
        parameters.append("Precipitation for wettest month: " + precip_month)
        if (precip_month != "") and (precip_month != string.whitespace) and (precip_month != "#"):
            precip_month_found = True
        else:
            precip_month_found = False

        # Soil texture raster
        soil_texture = sys.argv[14]
        parameters.append("Soil texture: " + soil_texture)
        if (soil_texture != "") and (soil_texture != string.whitespace) and (soil_texture != "#"):
            soil_texture_found = True
        else:
            soil_texture_found = False

        # Annual average precipitation raster
        precip_annual = sys.argv[15]
        parameters.append("Annual average precipitation: " + precip_annual)
        if (precip_annual != "") and (precip_annual != string.whitespace) and (precip_annual != "#"):
            precip_annual_found = True
        else:
            precip_annual_found = False

        # Annual actual evapotranspiration raster
        AET = sys.argv[16]
        parameters.append("Actual Evapotranspiration: " + soil_texture)
        if (AET != "") and (AET != string.whitespace) and (AET != "#"):
            aet_found = True
        else:
            aet_found = False

        # Threshold flow accumulation integer
        threshold_flowacc = sys.argv[17]
        parameters.append("Threshold flow accumulation: " + str(threshold_flowacc))
        if (threshold_flowacc != "") and (threshold_flowacc != string.whitespace) and (threshold_flowacc != "#"):
            threshold_flowacc_found = True
        else:
            threshold_flowacc_found = False

        # Riparian buffer distance (meters)
        buffer_dist = sys.argv[18]
        parameters.append("Riparian buffer distance: " + str(buffer_dist))
        if (buffer_dist != "") and (buffer_dist != string.whitespace) and (buffer_dist != "#"):
            buffer_dist_found = True
        else:
            buffer_dist_found = False

        # Watershed mask
        watershed = sys.argv[19]
        parameters.append("Watershed: " + str(watershed))
        if (watershed != "") and (watershed != string.whitespace) and (watershed != "#"):
            watershed_found = True
        else:
            watershed_found = False

        # Suffix to add to end of output filenames, as <filename>_<suffix>
        Suffix = sys.argv[20]
        parameters.append("Suffix: " + Suffix)
        
        if (Suffix == "") or (Suffix == string.whitespace) or (Suffix == "#"):
            Suffix = ""
        else:
            Suffix = "_" + Suffix

        # Make sure that at least one objective is chosen
        if do_erosion != 'true' and do_nutrient_n != 'true' and do_nutrient_p != 'true' and do_flood != 'true' and do_gw_bf != 'true':
            gp.AddError("\nError: No objectives were selected.  Please check boxes next to the objectives to be pre-processed.")
            raise Exception

        # Make sure that required inputs are provided for each objective chosen
        input_raster_list = []
        missing_data = 0

        if do_erosion == 'true':
            gp.AddMessage("\nErosion Control selected, checking required inputs:")
            
            if dem_found:
                gp.AddMessage("\tDEM")
                input_raster_list.append(DEM)
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, a DEM must be provided.\n")
                missing_data = 1
            if erosivity_found:
                gp.AddMessage("\tErosivity")
                input_raster_list.append(erosivity)
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, an Erosivity raster must be provided.\n")
                missing_data = 1
            if erodibility_found:
                gp.AddMessage("\tErodibility")
                input_raster_list.append(erodibility)
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, an Erodibility raster must be provided.\n")
                missing_data = 1
            if soil_depth_found:
                gp.AddMessage("\tSoil depth")
                input_raster_list.append(soil_depth)
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, a Soil Depth raster must be provided.\n")
                missing_data = 1
            if lulc_found:
                gp.AddMessage("\tLand use/land cover")
                input_raster_list.append(lulc)
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, a Land use / Land cover raster must be provided.\n")
                missing_data = 1
##            if lulc_general_table_found:
##                gp.AddMessage("\tLand use/land cover general class table")
##            else:
##                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, a Land use / Land cover general class mapping table must be provided.\n")
##                missing_data = 1
            if rios_coeff_table_found:
                gp.AddMessage("\tRIOS general coefficient table")
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, the RIOS general coefficient table must be provided.\n")
                missing_data = 1
            if threshold_flowacc_found:
                gp.AddMessage("\tThreshold flow accumulation")
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, a Threshold flow accumulation value must be provided.\n")
                missing_data = 1
            if buffer_dist_found:
                gp.AddMessage("\tRiparian buffer distance")
            else:
                gp.AddError("\n\tMissing Data: If Erosion Control is to be processed, a Riparian buffer distance value must be provided.\n")
                missing_data = 1

        if do_nutrient_p == 'true':
            gp.AddMessage("\nPhosphorus Retention selected, checking required inputs:")
            
            if dem_found:
                gp.AddMessage("\tDEM")
                if DEM not in input_raster_list:
                    input_raster_list.append(DEM)
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, a DEM must be provided.\n")
                missing_data = 1
            if erosivity_found:
                gp.AddMessage("\tErosivity")
                if erosivity not in input_raster_list:
                    input_raster_list.append(erosivity)
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, an Erosivity raster must be provided.\n")
                missing_data = 1
            if erodibility_found:
                gp.AddMessage("\tErodibility")
                if erodibility not in input_raster_list:
                    input_raster_list.append(erodibility)
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, an Erodibility raster must be provided.\n")
                missing_data = 1
            if soil_depth_found:
                gp.AddMessage("\tSoil depth")
                if soil_depth not in input_raster_list:
                    input_raster_list.append(soil_depth)
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, a Soil Depth raster must be provided.\n")
                missing_data = 1
            if lulc_found:
                gp.AddMessage("\tLand use/land cover")
                if lulc not in input_raster_list:
                    input_raster_list.append(lulc)
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, a Land use / Land cover raster must be provided.\n")
                missing_data = 1
##            if lulc_general_table_found:
##                gp.AddMessage("\tLand use/land cover general class table")
##            else:
##                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, a Land use / Land cover general class mapping table must be provided.\n")
##                missing_data = 1
            if rios_coeff_table_found:
                gp.AddMessage("\tRIOS general coefficient table")
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, the RIOS general coefficient table must be provided.\n")
                missing_data = 1
            if threshold_flowacc_found:
                gp.AddMessage("\tThreshold flow accumulation")
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, a Threshold flow accumulation value must be provided.\n")
                missing_data = 1
            if buffer_dist_found:
                gp.AddMessage("\tRiparian buffer distance")
            else:
                gp.AddError("\n\tMissing Data: If Phosphorus Retention is to be processed, a Riparian buffer distance value must be provided.\n")
                missing_data = 1

        if do_nutrient_n == 'true':
            gp.AddMessage("\nNitrogen Retention selected, checking required inputs:")
            
            if dem_found:
                gp.AddMessage("\tDEM")
                if DEM not in input_raster_list:
                    input_raster_list.append(DEM)
            else:
                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, a DEM must be provided.\n")
                missing_data = 1
            if soil_depth_found:
                gp.AddMessage("\tSoil depth")
                if soil_depth not in input_raster_list:
                    input_raster_list.append(soil_depth)
            else:
                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, a Soil Depth raster must be provided.\n")
                missing_data = 1
            if lulc_found:
                gp.AddMessage("\tLand use/land cover")
                if lulc not in input_raster_list:
                    input_raster_list.append(lulc)
            else:
                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, a Land use / Land cover raster must be provided.\n")
                missing_data = 1
##            if lulc_general_table_found:
##                gp.AddMessage("\tLand use/land cover general class table")
##            else:
##                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, a Land use / Land cover general class mapping table must be provided.\n")
##                missing_data = 1
            if rios_coeff_table_found:
                gp.AddMessage("\tRIOS general coefficient table")
            else:
                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, the RIOS general coefficient table must be provided.\n")
                missing_data = 1
            if threshold_flowacc_found:
                gp.AddMessage("\tThreshold flow accumulation")
            else:
                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, a Threshold flow accumulation value must be provided.\n")
                missing_data = 1
            if buffer_dist_found:
                gp.AddMessage("\tRiparian buffer distance")
            else:
                gp.AddError("\n\tMissing Data: If Nitrogen Retention is to be processed, a Riparian buffer distance value must be provided.\n")
                missing_data = 1

        if do_flood == 'true':
            gp.AddMessage("\nFlood Mitigation selected, checking required inputs:")
            
            if dem_found:
                gp.AddMessage("\tDEM")
                if DEM not in input_raster_list:
                    input_raster_list.append(DEM)
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, a DEM must be provided.\n")
                missing_data = 1
            if precip_month_found:
                gp.AddMessage("\tPrecipitation depth for wettest month")
                input_raster_list.append(precip_month)
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, a Precipitation depth for wettest month raster must be provided.\n")
                missing_data = 1 
            if soil_texture_found:
                gp.AddMessage("\tSoil texture")
                input_raster_list.append(soil_texture)
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, a Soil Texture raster must be provided.\n")
                missing_data = 1
            if lulc_found:
                gp.AddMessage("\tLand use/land cover")
                if lulc not in input_raster_list:
                    input_raster_list.append(lulc)
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, a Land use / Land cover raster must be provided.\n")
                missing_data = 1
##            if lulc_general_table_found:
##                gp.AddMessage("\tLand use/land cover general class table")
##            else:
##                gp.AddError("\n\tMissing Data If Flood Mitigation is to be processed, a Land use / Land cover general class mapping table must be provided.\n")
##                missing_data = 1
            if rios_coeff_table_found:
                gp.AddMessage("\tRIOS general coefficient table")
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, the RIOS general coefficient table must be provided.\n")
                missing_data = 1
            if threshold_flowacc_found:
                gp.AddMessage("\tThreshold flow accumulation")
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, a Threshold flow accumulation value must be provided.\n")
                missing_data = 1
            if buffer_dist_found:
                gp.AddMessage("\tRiparian buffer distance")
            else:
                gp.AddError("\n\tMissing Data: If Flood Mitigation is to be processed, a Riparian buffer distance value must be provided.\n")
                missing_data = 1

        if do_gw_bf == 'true':
            gp.AddMessage("\nGroundwater Recharge/Baseflow selected, checking required inputs:")
            
            if dem_found:
                gp.AddMessage("\tDEM")
                if DEM not in input_raster_list:
                    input_raster_list.append(DEM)
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, a DEM must be provided.\n")
                missing_data = 1
            if precip_annual_found:
                gp.AddMessage("\tAnnual average precipitation")
                input_raster_list.append(precip_annual)
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, an Annual Average Precipitation raster must be provided.\n")
                missing_data = 1
            if aet_found:
                gp.AddMessage("\tActual Evapotranspiration")
                input_raster_list.append(AET)
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, an Actual Evapotranspiration raster must be provided.\n")
                missing_data = 1
            if lulc_found:
                gp.AddMessage("\tLand use/land cover")
                if lulc not in input_raster_list:
                    input_raster_list.append(lulc)
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, a Land use / Land cover raster must be provided.\n")
                missing_data = 1
##            if lulc_general_table_found:
##                gp.AddMessage("\tLand use/land cover general class table")
##            else:
##                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, a Land use / Land cover general class mapping table must be provided.\n")
##                missing_data = 1
            if rios_coeff_table_found:
                gp.AddMessage("\tRIOS general coefficient table")
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, the RIOS general coefficient table must be provided.\n")
                missing_data = 1
            if soil_texture_found:
                gp.AddMessage("\tSoil texture")
                if soil_texture not in input_raster_list:
                    input_raster_list.append(soil_texture)
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, a Soil Texture raster must be provided.\n")
                missing_data = 1
            if soil_depth_found:
                gp.AddMessage("\tSoil depth")
                if soil_depth not in input_raster_list:
                    input_raster_list.append(soil_depth)
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, a Soil Depth raster must be provided.\n")
                missing_data = 1
            if threshold_flowacc_found:
                gp.AddMessage("\tThreshold flow accumulation")
            else:
                gp.AddError("\n\tMissing Data: If Groundwater Recharge/Baseflow is to be processed, a Threshold flow accumulation value must be provided.\n")
                missing_data = 1

        if missing_data == 1:
            gp.AddError("\n\nPlease consult the tool's Help information and enter all of the required data inputs. \n")
            raise Exception

    except:
        gp.AddError("\nError specifying input data: " + gp.GetMessages(2))
        raise Exception


    ### Check and create output folders and files
    try:
        thefolders=["Output","Intermediate"]
        for folder in thefolders:
            if not gp.exists(gp.workspace + folder):
                gp.CreateFolder_management(gp.workspace, folder)
    except:
        gp.AddError( "\nError creating output folders: " + gp.GetMessages(2))
        raise Exception



    # Output files
    
    try:
        # Output directories
        outputws = gp.workspace + os.sep +  "Output" + os.sep
        interws = gp.workspace + os.sep + "Intermediate" + os.sep

        # Intermediate files
        lulc_coeffs = interws + "lulc_coeffs"
        flowdir_channels = interws + "flowdir_chan"

        slope_index = interws + "slope_idx"
        erosivity_index = interws + "eros_idx"
        erodibility_index = interws + "erod_idx"
        soil_depth_norm = interws + "sdepth_norm"
        soil_depth_index = interws + "sdepth_idx"
        
        erosion_comb_weight_R = interws + "er_cwgt_r"
        erosion_comb_weight_Exp = interws + "er_cwgt_e"
        erosion_index_exp = interws + "er_ind_e"
        erosion_index_ret = interws + "er_ind_r"
        erosion_ups_flowacc = interws + "er_flowacc"
        erosion_dret_flowlen = interws + "er_flowlen"

        phos_index_exp = interws + "p_ind_e"
        phos_index_ret = interws + "p_ind_r"
        phos_comb_weight_R = interws + "p_cwgt_r"
        phos_comb_weight_Exp = interws + "p_cwgt_e"
        phos_ups_flowacc = interws + "p_flowacc"
        phos_dret_flowlen = interws + "p_flowlen"

        nit_index_exp = interws + "n_ind_e"
        nit_index_ret = interws + "n_ind_r"
        nit_comb_weight_R = interws + "n_cwgt_r"
        nit_comb_weight_Exp = interws + "n_cwgt_e"
        nit_ups_flowacc = interws + "n_flowacc"
        nit_dret_flowlen = interws + "n_flowlen"

        flgw_index_cover = interws + "fg_ind_c"
        flgw_index_rough = interws + "fg_ind_r"
        flood_rainfall_depth_index = interws + "fl_rain_idx"
        flood_comb_weight_ret = interws + "fl_cwgt_r"
        flood_comb_weight_source = interws + "fl_cwgt_s"
        flood_ups_flowacc = interws + "fl_flowacc"
        flood_dret_flowlen = interws + "fl_flowlen"

        gwater_precip_annual_index = interws + "gw_prec_idx"
        gwater_aet_index = interws + "gw_aet_idx"
        gwater_comb_weight_ret = interws + "gw_cwgt_r"
        gwater_comb_weight_source = interws + "gw_cwgt_s"
        gwater_ups_flowacc = interws + "gw_flowacc"
        gwater_dret_flowlen = interws + "gw_flowlen"
        

        # LULC coefficient table field names
        lulc_gen_field = "lulc_gen"
        sed_ret_field = "sed_ret"
        sed_exp_field = "sed_exp"

        # Field names in RIOS coefficient table
        lucode_field = "lucode"
        lugen_rios_field = "LULC_general"
        sed_ret_rios_field = "Sed_Ret"
        sed_exp_rios_field = "Sed_Exp"
        n_exp_rios_field = "N_Exp"
        n_ret_rios_field = "N_Ret"
        p_exp_rios_field = "P_Exp"
        p_ret_rios_field = "P_Ret"
        roughness_rios_field = "Rough_Rank"
        cover_rios_field = "Cover_Rank"
        rios_fields = [sed_ret_rios_field, sed_exp_rios_field, n_exp_rios_field, n_ret_rios_field, p_exp_rios_field,p_ret_rios_field, roughness_rios_field, cover_rios_field]

        # Keep track of whether frequently-used layers have been created in this run
        # Want to override previous runs, but re-use current versions
        made_lulc_coeffs = False
        made_flowdir_channels = False
        made_slope_index = False
        made_flood_slope_index = False
        made_gwater_slope_index = False
        made_soil_depth_index = False
        made_erosivity_index = False
        made_erodibility_index = False
        made_flgw_index_cover = False
        made_flgw_index_rough = False

        
        # Outputs

        streams_line = outputws + "streams_" + str(threshold_flowacc) + Suffix + ".shp"
        erosion_dret_index = outputws + "erosion_downslope_retention_index" + Suffix + ".tif"
        erosion_upslope_source = outputws + "erosion_upslope_source" + Suffix + ".tif"
        erosion_riparian_index = outputws + "erosion_riparian_index" + Suffix + ".tif"

        phos_dret_index = outputws + "phosphorus_downslope_retention_index" + Suffix + ".tif"
        phos_upslope_source = outputws + "phosphorus_upslope_source" + Suffix + ".tif"
        phos_riparian_index = outputws + "phosphorus_riparian_index" + Suffix + ".tif"

        nit_dret_index = outputws + "nitrogen_downslope_retention_index" + Suffix + ".tif"
        nit_upslope_source = outputws + "nitrogen_upslope_source" + Suffix + ".tif"
        nit_riparian_index = outputws + "nitrogen_riparian_index" + Suffix + ".tif"

        flood_dret_index = outputws + "flood_downslope_retention_index" + Suffix + ".tif"
        flood_upslope_source = outputws + "flood_upslope_source" + Suffix + ".tif"
        flood_riparian_index = outputws + "flood_riparian_index" + Suffix + ".tif"
        flood_slope_index = outputws + "flood_slope_index" + Suffix + ".tif"

        gwater_dret_index = outputws + "gwater_bflow_downslope_retention_index" + Suffix + ".tif"
        gwater_upslope_source = outputws + "gwater_bflow_upslope_source" + Suffix + ".tif"
        gwater_riparian_index = outputws + "gwater_bflow_riparian_index" + Suffix + ".tif"
        gwater_slope_index = outputws + "gwater_bflow_slope_index" + Suffix + ".tif"

    except:
        gp.AddError( "\nError configuring local variables: " + gp.GetMessages(2))
        raise Exception



    ### Check input raster projections - they should all be the same
    try:
        gp.AddMessage("\nChecking input raster projections...")
        DEMDesc = gp.describe(DEM)
        DEMspatref = DEMDesc.SpatialReference
        
        rasters = input_raster_list
        for x in rasters:
            rasterDesc=gp.describe(x)
            spatreflc = rasterDesc.SpatialReference
            if spatreflc.Type <> 'Projected':
                gp.AddMessage(x + " does not appear to be projected.  It is assumed to be in meters.")
            elif spatreflc.LinearUnitName <> 'Meter':
                gp.AddMessage("This model assumes that data in " + x + " is projected in meters.  You may get erroneous results")
            if str(DEMspatref.name) <> str(spatreflc.name):
                gp.AddError("\nError: " + x + " is not in the same coordinate system as the DEM.  " + x + " is projected in " + spatreflc.name + " while the DEM is in " + DEMspatref.name + ".  Please project raster in the same projection as the DEM.\n")  
                raise Exception
    except:
        gp.AddError("\nError checking input raster projections: " + gp.GetMessages(2)) 
        raise Exception

    
    ### Set the Geoprocessing environment
    try:
        install_info = gp.GetInstallInfo("desktop")
        # Make sure all temporary files go in the Intermediate folder
        gp.workspace = interws
        # Use minimum cell size of all input rasters
        gp.cellSize = "MINOF"
        # Make sure all outputs align with the land cover map
        gp.snapRaster = lulc
        gp.Extent = lulc
        # If a watershed mask is provided, use it to minimize processing time
        if watershed_found:
            gp.Mask = watershed

    except:
        gp.AddError( "\nError setting geoprocessing environment: " + gp.GetMessages(2))
        raise Exception



    ### Preprocess DEM derivatives
    
    try:
        if not gp.exists(outputws + "Hydro_layers"):
            gp.CreateFolder_management(outputws, "Hydro_layers")
            gp.AddMessage("\nCreating hydrology layers...")
        Hydrows = outputws + "Hydro_layers" + os.sep
        if not gp.exists(Hydrows + "flow_dir"):
            # Create flow direction raster
            gp.FlowDirection_sa(DEM, Hydrows + "flow_dir", "NORMAL")

        flow_dir = Hydrows + "flow_dir"

        if not gp.exists(Hydrows + "slope"):
            # Create slope raster 
            gp.Slope_sa(DEM, Hydrows + "slope", "PERCENT_RISE", "1")
            
        slope = Hydrows + "slope"            
            
        if not gp.exists(Hydrows + "flow_acc"):
            # Create flow accumulation raster
            gp.FlowAccumulation_sa(Hydrows + "flow_dir", Hydrows + "flow_acc", "", "FLOAT")

        flow_acc = Hydrows + "flow_acc"
        
    except:
        gp.AddError("\nError processing hydrology layers: " + gp.GetMessages(2))
        raise Exception


    # Check for existence of a specific field name in a layer
    def confirmfield(field, target):
        try:
            thefields = gp.ListFields(target, field, "All")
            field = thefields.next()
            if field:
                return True
            else:
                return False

        except:
            gp.AddError ("\nError confirming field " + str(field) + " in table " + str(target) + ": " + gp.GetMessages(2))
            raise Exception


    ### Verify required input table fields' existence and type

    def checkfields (fields, table):
        
        try:

            table_fields = gp.listfields(table, "*", "All")
            table_field = table_fields.next()

            foundfields = []
            while (table_field):
                foundfields.append(table_field.Name.upper())
                table_field = table_fields.next()

            # Make sure that all required fields are in the input table 
            for f in fields:
                if not f.upper() in foundfields:
                    gp.AddError("\nError: Required table field " + str(f) + " not found in input table " + str(table) + "\n")
                    raise Exception

        except:
            gp.AddError ("\nError verifying input table fields:  " + gp.GetMessages(2))
            raise Exception


    # Set flow direction raster to null where there are streams

    def define_channels():

        try:
            gp.AddMessage("\n\tDefining flow direction channels...")
            lyrFAC = "lyrFAC"
            lyrFDIR = "lyrFDIR"
            gp.MakeRasterLayer(flow_acc,lyrFAC)
            gp.MakeRasterLayer(flow_dir,lyrFDIR)
            expr = "con(%s <= %s, %s)" % (lyrFAC, str(int(threshold_flowacc)),lyrFDIR)
            gp.SingleOutputMapAlgebra_sa(expr, flowdir_channels)
            
        except:
            gp.AddError ("\nError defining flow direction channels:  " + gp.GetMessages(2))
            raise Exception


    # Normalize raster, using the max value for that raster
    
    def normalize(in_raster, out_raster):
        try:
            raster_max = gp.GetRasterProperties_management(in_raster, "MAXIMUM")
            gp.SingleOutputMapAlgebra_sa("FLOAT(" + in_raster + ") / " + str(float(raster_max)), out_raster)
        except:
            gp.AddError ("\nError normalizing raster " + str(in_raster) + ":  " + gp.GetMessages(2))
            raise Exception


    # Map general LULC classes and coefficient table to user's landcover

    def map_coefficients():

        try:
            gp.AddMessage("\n\tMapping coefficients to landcover...")

            # intermediate files
            lulc_gen_join = interws + "lu_gen_join"
            lulc_copy = interws + "lulc_copy"
            
            gp.CopyRaster_management(lulc, lulc_copy)

            if not confirmfield(lulc_gen_field, lulc_copy):
                gp.AddField(lulc_copy, lulc_gen_field, "LONG")

            # Remove any fields that conflict with the coefficient table input field names
            for field in rios_fields:
                if confirmfield(field, lulc_copy):
                    gp.DeleteField(lulc_copy, field)            

            # Map land cover map to coefficient table via the lucode
            gp.MakeRasterLayer_management(lulc_copy, "lulc_layer")
            gp.MakeTableView_management(rios_coeff_table, "rios_coeff_layer")
            gp.AddJoin("lulc_layer", "VALUE", "rios_coeff_layer", lucode_field, "KEEP_COMMON")
            gp.CopyRaster_management("lulc_layer", lulc_coeffs)
            

###### PRE- RIOS 1.0.0 code

##            # Map general classes to landuse table via the lucode
##            gp.MakeTableView_management(lulc_general_table, "lulc_gen_layer")
##            gp.AddJoin("lulc_layer", "VALUE", "lulc_gen_layer", lucode_field, "KEEP_COMMON")
##            gp.CopyRaster_management("lulc_layer", lulc_gen_join)
##            gp.CalculateField_management(lulc_gen_join, lulc_gen_field, "[" + lugen_rios_field + "]", "VB")

##            # Map coefficients to user's landuse table via the general classes
##            gp.MakeRasterLayer_management(lulc_gen_join, "lulc_gen_join_layer")
##            gp.MakeTableView_management(rios_coeff_table, "rios_coeff_layer")
##            gp.AddJoin("lulc_gen_join_layer", lulc_gen_field, "rios_coeff_layer", lugen_rios_field)
##            gp.CopyRaster_management("lulc_gen_join_layer", lulc_coeffs)

        except:
            gp.AddError ("\nError mapping coefficients to landcover:  " + gp.GetMessages(2))
            raise Exception


    # Create riparian index

    def riparian_index(retention_index, out_rindex, cont_index_mosaic_filename):
        try:
            # Intermediate files
            streams_ras = interws + "streams_ras"
            buffer_left = interws + "buffer_left.shp"
            buffer_right = interws + "buffer_right.shp"
            retention_left = interws + "ret_left"
            retention_right = interws + "ret_right"
            cont_index_left = interws + "cind_left"
            cont_index_right = interws + "cind_right"
            cont_index_left_clip = interws + "cind_left_cl"
            cont_index_right_clip = interws + "cind_right_cl"
            cont_index_mosaic = interws + cont_index_mosaic_filename
            one = interws + "one"
            
            gp.AddMessage("\n\tCreating riparian continuity index...")
                            
            # Create stream network where flow accumulation > input threshold
            gp.SingleOutputMapAlgebra_sa("CON(" + flow_acc + " > " + str(threshold_flowacc) + ", 1)", streams_ras)
            # See if this produces better stream output than StreamToFeature
            gp.RasterToPolyline_conversion(streams_ras, streams_line, "NODATA", 0, "NO_SIMPLIFY")
##            gp.StreamToFeature_sa(streams_ras, flow_dir, streams_line, "NO_SIMPLIFY")
            # Output the stream layer so the user can compare with a known correct stream layer
            # to determine the correct threshold flow accumulation value
            gp.AddMessage("\n\tCreated stream layer " + str(streams_line))

            # Create buffers around streams
            gp.Buffer_analysis(streams_line, buffer_left, buffer_dist, "LEFT", "#", "ALL")
            gp.Buffer_analysis(streams_line, buffer_right, buffer_dist, "RIGHT", "#", "ALL")

            # Clip retention index with buffers
            gp.ExtractByMask_sa(retention_index, buffer_left, retention_left)
            gp.ExtractByMask_sa(retention_index, buffer_right, retention_right)

            # Continuity index for each buffer
            gp.FocalStatistics_sa(retention_left, cont_index_left, "RECTANGLE 3 3 CELL", "MEAN")
            gp.FocalStatistics_sa(retention_right, cont_index_right, "RECTANGLE 3 3 CELL", "MEAN")
            gp.ExtractByMask_sa(cont_index_left, buffer_left, cont_index_left_clip)
            gp.ExtractByMask_sa(cont_index_right, buffer_right, cont_index_right_clip)
            
            # Mosaic them back together
            # Set extent, otherwise there may be clipping due to stream network being smaller than whole watershed
            desc = gp.Describe(retention_index)
            saveExtent = gp.Extent
            gp.Extent = desc.Extent
            gp.Mosaic_management(cont_index_left_clip, cont_index_right_clip, "MAXIMUM")
            gp.Extent = saveExtent

            # Final riparian continuity index
##            gp.Minus_sa("1.0", cont_index_right_clip, out_rindex)
            gp.CopyRaster_management(cont_index_right_clip, out_rindex)
            
        except:
            gp.AddError ("\nError creating riparian continuity index:  " + gp.GetMessages(2))
            raise Exception


    ### Process Erosion Control objective

    if do_erosion == 'true':

        try: 
            gp.AddMessage("\n\nProcessing Erosion Control objective...")

##            checkfields ([lugen_rios_field, lucode_field], lulc_general_table)

            ## LULC Index-R

            if not made_lulc_coeffs:
                map_coefficients()
                made_lulc_coeffs = True

            # Make Export and Retention Index rasters
            gp.Lookup_sa(lulc_coeffs, sed_exp_rios_field, erosion_index_exp)
            gp.Lookup_sa(lulc_coeffs, sed_ret_rios_field, erosion_index_ret)

            gp.AddMessage("\n\tCreating downslope retention index...")
            
            ## Combined weight retention
            if not made_slope_index:
                normalize(slope, slope_index)
                made_slope_index = True
            gp.SingleOutputMapAlgebra_sa("((1.0 - " + slope_index + " ) + " + erosion_index_ret + ") / 2", erosion_comb_weight_R)

            # Set flow direction raster to null where there are streams
            if not made_flowdir_channels: 
                define_channels()
                made_flowdir_channels = True

            ## Downslope retention index
##            gp.AddMessage("\nDEBUG: SKIPPING doing flow length!!!!")
##            raise Exception
        
            gp.FlowLength_sa(flowdir_channels, erosion_dret_flowlen, "DOWNSTREAM", erosion_comb_weight_R)
            normalize(erosion_dret_flowlen, erosion_dret_index)
            gp.AddMessage("\n\tCreated Erosion downslope retention index: " + erosion_dret_index)

            gp.AddMessage("\n\tCreating upslope source...")

            # Erosivity index
            if not made_erosivity_index:
                normalize(erosivity, erosivity_index)
                made_erosivity_index = True

            # Erodibility index
            if not made_erodibility_index:
                normalize(erodibility, erodibility_index)
                made_erodibility_index = True

            # Soil depth index
            if not made_soil_depth_index:
                normalize(soil_depth, soil_depth_norm)
                gp.Minus_sa("1.0", soil_depth_norm, soil_depth_index)
                made_soil_depth_index = True
                
            # Combined weight export
            gp.SingleOutputMapAlgebra_sa("(" + slope_index + " + " + erosivity_index + " + " + erodibility_index + \
                                         " + " + soil_depth_index + " + (1 - " + erosion_index_ret + ") + " + \
                                         erosion_index_exp + ") / 6", erosion_comb_weight_Exp)

            ## Upslope source
            ## Not an index because we're not normalizing in this script
##            gp.AddMessage("\nDEBUG: SKIPPING doing flow acc!!!!")
            gp.FlowAccumulation_sa(flow_dir, erosion_upslope_source, erosion_comb_weight_Exp)
            gp.AddMessage("\n\tCreated Erosion upslope source: " + erosion_upslope_source)

            ## Riparian continuity
            
            # Only ArcInfo supports one-sided buffers, and no workaround has been found
            # so the riparian index factor can only be calculated with an ArcInfo license
            if gp.ProductInfo() != "ArcInfo":
                gp.AddError("\nSorry, the Riparian Continuity index can only currently be calculated with an ArcInfo license.")
                gp.AddError("\nThe Riparian Continuity index will not be created.")
            else:
                riparian_index(erosion_index_ret, erosion_riparian_index, "eros_mosaic")
                gp.AddMessage("\n\tCreated Erosion riparian continuity index: " + erosion_riparian_index)
        
        except:
            gp.AddError ("\nError processing Erosion Control objective:  " + gp.GetMessages(2))
            raise Exception


    ### Process Phosphorus Retention objective

    if do_nutrient_p == 'true':

        try: 
            gp.AddMessage("\n\nProcessing Phosphorus Retention objective...")

##            checkfields ([lugen_rios_field, lucode_field], lulc_general_table)

            ## LULC Index-R

            if not made_lulc_coeffs:
                map_coefficients()
                made_lulc_coeffs = True

            # Make Export and Retention Index rasters
            gp.Lookup_sa(lulc_coeffs, p_exp_rios_field, phos_index_exp)
            gp.Lookup_sa(lulc_coeffs, p_ret_rios_field, phos_index_ret)

            gp.AddMessage("\n\tCreating downslope retention index...")
            
            ## Combined weight retention
            if not made_slope_index:
                normalize(slope, slope_index)
                made_slope_index = True

            gp.SingleOutputMapAlgebra_sa("((1.0 - " + slope_index + " ) + " + phos_index_ret + ") / 2", phos_comb_weight_R)

            # Set flow direction raster to null where there are streams
            if not made_flowdir_channels: 
                define_channels()
                made_flowdir_channels = True

            ## Downslope retention index
            gp.FlowLength_sa(flowdir_channels, phos_dret_flowlen, "DOWNSTREAM", phos_comb_weight_R)
            normalize(phos_dret_flowlen, phos_dret_index)
            gp.AddMessage("\n\tCreated Phosphorus downslope retention index: " + phos_dret_index)

            gp.AddMessage("\n\tCreating upslope source...")
            
            # Erosivity index
            if not made_erosivity_index:
                normalize(erosivity, erosivity_index)
                made_erosivity_index = True

            # Erodibility index
            if not made_erodibility_index:
                normalize(erodibility, erodibility_index)
                made_erodibility_index = True

            # Soil depth index
            if not made_soil_depth_index:
                normalize(soil_depth, soil_depth_norm)
                gp.Minus_sa("1.0", soil_depth_norm, soil_depth_index)
                made_soil_depth_index = True
                
            # Combined weight export
            gp.SingleOutputMapAlgebra_sa("(" + slope_index + " + " + erosivity_index + " + " + erodibility_index + \
                                         " + " + soil_depth_index + " + (1 - " + phos_index_ret + ") + " + \
                                         phos_index_exp + ") / 6", phos_comb_weight_Exp)

            ## Upslope source
            gp.FlowAccumulation_sa(flow_dir, phos_upslope_source, phos_comb_weight_Exp)
            gp.AddMessage("\n\tCreated Phosphorus upslope source: " + phos_upslope_source)

            ## Riparian continuity
            
            # Only ArcInfo supports one-sided buffers, and no workaround has been found
            # so the riparian index factor can only be calculated with an ArcInfo license
            if gp.ProductInfo() != "ArcInfo":
                gp.AddError("\nSorry, the Riparian Index can only currently be calculated with an ArcInfo license.")
                gp.AddError("\nThe Riparian Continuity index will not be created.")
            else:
                riparian_index(phos_index_ret, phos_riparian_index, "phos_mosaic")
                gp.AddMessage("\n\tCreated Phosphorus riparian continuity index: " + phos_riparian_index)
        
        except:
            gp.AddError ("\nError processing Phosphorus Retention objective:  " + gp.GetMessages(2))
            raise Exception


    ### Process Nitrogen Retention objective

    if do_nutrient_n == 'true':

        try: 
            gp.AddMessage("\n\nProcessing Nitrogen Retention objective...")

##            checkfields ([lugen_rios_field, lucode_field], lulc_general_table)

            ## LULC Index-R

            if not made_lulc_coeffs:
                map_coefficients()
                made_lulc_coeffs = True

            # Make Export and Retention Index rasters
            gp.Lookup_sa(lulc_coeffs, n_exp_rios_field, nit_index_exp)
            gp.Lookup_sa(lulc_coeffs, n_ret_rios_field, nit_index_ret)

            gp.AddMessage("\n\tCreating downslope retention index...")
            
            ## Combined weight retention
            if not made_slope_index:
                normalize(slope, slope_index)
                made_slope_index = True
                
            gp.SingleOutputMapAlgebra_sa("((1.0 - " + slope_index + " ) + " + nit_index_ret + ") / 2", nit_comb_weight_R)

            # Set flow direction raster to null where there are streams
            if not made_flowdir_channels: 
                define_channels()
                made_flowdir_channels = True

            ## Downslope retention index
            gp.FlowLength_sa(flowdir_channels, nit_dret_flowlen, "DOWNSTREAM", nit_comb_weight_R)
            normalize(nit_dret_flowlen, nit_dret_index)
            gp.AddMessage("\n\tCreated Nitrogen downslope retention index: " + nit_dret_index)

            gp.AddMessage("\n\tCreating upslope source...")
            
            # Soil depth index
            if not made_soil_depth_index:
                normalize(soil_depth, soil_depth_norm)
                gp.Minus_sa("1.0", soil_depth_norm, soil_depth_index)
                made_soil_depth_index = True
                
            # Combined weight export
            gp.SingleOutputMapAlgebra_sa("(" + slope_index + " + " + soil_depth_index + \
                                          " + (1 - " + nit_index_ret + ") + " + \
                                         nit_index_exp + ") / 4", nit_comb_weight_Exp)

            ## Upslope source
            gp.FlowAccumulation_sa(flow_dir, nit_upslope_source, nit_comb_weight_Exp)
            gp.AddMessage("\n\tCreated Nitrogen upslope source: " + nit_upslope_source)

            ## Riparian continuity
            
            # Only ArcInfo supports one-sided buffers, and no workaround has been found
            # so the riparian index factor can only be calculated with an ArcInfo license
            if gp.ProductInfo() != "ArcInfo":
                gp.AddError("\nSorry, the Riparian Index can only currently be calculated with an ArcInfo license.")
                gp.AddError("\nThe Riparian Continuity index will not be created.")
            else:
                riparian_index(nit_index_ret, nit_riparian_index, "nit_mosaic")
                gp.AddMessage("\n\tCreated Nitrogen riparian continuity index: " + nit_riparian_index)
        
        except:
            gp.AddError ("\nError processing Nitrogen Retention objective:  " + gp.GetMessages(2))
            raise Exception


    ### Process Flood Mitigation objective

    if do_flood == 'true':

        try: 
            gp.AddMessage("\n\nProcessing Flood Mitigation objective...")

##            checkfields ([lugen_rios_field, lucode_field], lulc_general_table)

            ## LULC Index-R

            if not made_lulc_coeffs:
                map_coefficients()
                made_lulc_coeffs = True

            # Make Cover and Roughness Index rasters
            if not made_flgw_index_cover:
                gp.Lookup_sa(lulc_coeffs, cover_rios_field, flgw_index_cover)
                made_flgw_index_cover = True
            if not made_flgw_index_rough:
                gp.Lookup_sa(lulc_coeffs, roughness_rios_field, flgw_index_rough)
                made_flgw_index_rough = True

            ## Riparian continuity
            
            # Only ArcInfo supports one-sided buffers, and no workaround has been found
            # so the riparian index factor can only be calculated with an ArcInfo license
            if gp.ProductInfo() != "ArcInfo":
                gp.AddError("\nSorry, the Riparian Index can only currently be calculated with an ArcInfo license.")
                gp.AddError("\nThe Riparian Continuity index will not be created.")
            else:
                riparian_index(flgw_index_rough, flood_riparian_index, "flood_mosaic")
                gp.AddMessage("\n\tCreated Flood Mitigation riparian continuity index: " + flood_riparian_index)

            ## Slope index - binned, not normalized
            gp.AddMessage("\n\tCreating slope index...")
            if not made_flood_slope_index:
                gp.SingleOutputMapAlgebra_sa("CON(" + slope + " >= 10.001, 1.0, CON(" \
                                             + slope + " > 5.001 && " + slope + " <= 10.0, 0.66, 0.33))", flood_slope_index)
                made_flood_slope_index = True

            gp.AddMessage("\n\tCreated Flood slope index: " + flood_slope_index)
            
            # Combined weight R
            gp.AddMessage("\n\tCreating downslope retention index...")
            gp.SingleOutputMapAlgebra_sa("((1.0 - " + flood_slope_index + " ) + " + flgw_index_rough + ") / 2", flood_comb_weight_ret)
            
            # Set flow direction raster to null where there are streams
            if not made_flowdir_channels: 
                define_channels()
                made_flowdir_channels = True

            ## Downslope retention index
            gp.FlowLength_sa(flowdir_channels, flood_dret_flowlen, "DOWNSTREAM", flood_comb_weight_ret)
            normalize(flood_dret_flowlen, flood_dret_index)
            gp.AddMessage("\n\tCreated Flood Mitigation downslope retention index: " + flood_dret_index)

            gp.AddMessage("\n\tCreating upslope source...")
            
            # Rainfall depth index
            normalize(precip_month, flood_rainfall_depth_index)
                
            # Combined weight source
            gp.SingleOutputMapAlgebra_sa("(" + flood_rainfall_depth_index + " + " + "(1 - " + flgw_index_cover + \
                                         ") + " + soil_texture + " + " + flood_slope_index + \
                                         " + (1 - " + flgw_index_rough + ")) / 5" , flood_comb_weight_source)

            ## Upslope source
            gp.FlowAccumulation_sa(flow_dir, flood_upslope_source, flood_comb_weight_source)
            gp.AddMessage("\n\tCreated Flood Mitigation upslope source: " + flood_upslope_source)
        
        except:
            gp.AddError ("\nError processing Flood Mitigation objective:  " + gp.GetMessages(2))
            raise Exception


    ### Process Groundwater Recharge/Baseflow objective
    if do_gw_bf == 'true':

        try: 
            gp.AddMessage("\n\nProcessing Groundwater Recharge/Baseflow objective...")

##            checkfields ([lugen_rios_field, lucode_field], lulc_general_table)

            ## LULC Index-R

            if not made_lulc_coeffs:
                map_coefficients()
                made_lulc_coeffs = True


            # Make Cover and Roughness Index rasters
            if not made_flgw_index_cover:
                gp.Lookup_sa(lulc_coeffs, roughness_rios_field, flgw_index_cover)
                made_flgw_index_cover = True
            if not made_flgw_index_rough:
                gp.Lookup_sa(lulc_coeffs, cover_rios_field, flgw_index_rough)
                made_flgw_index_rough = True

            ## Slope index - binned, not normalized, use Flood's slope index if it was created
            gp.AddMessage("\n\tCreating slope index...")
            if do_flood == 'true' and gp.Exists(flood_slope_index):
                gp.CopyRaster_management(flood_slope_index, gwater_slope_index)
            else:
                gp.SingleOutputMapAlgebra_sa("CON(" + slope + " >= 10.001, 1.0, CON(" \
                                             + slope + " > 5.001 && " + slope + " <= 10.0, 0.66, 0.33))", gwater_slope_index)
                made_gwater_slope_index = True

            gp.AddMessage("\n\tCreated Groundwater/Baseflow slope index: " + gwater_slope_index)

            # If Flood was already done, use its outputs instead of re-calculating, since many are the same
            gp.AddMessage("\n\tCreating downslope retention index...")
            if do_flood == 'true' and gp.Exists(flood_dret_index):
                gp.CopyRaster_management(flood_dret_index, gwater_dret_index)
            else:
                # Combined weight R
                gp.SingleOutputMapAlgebra_sa("((1.0 - " + gwater_slope_index + " ) + " + flgw_index_rough + ") / 2", gwater_comb_weight_ret)

                # Set flow direction raster to null where there are streams
                if not made_flowdir_channels: 
                    define_channels()
                    made_flowdir_channels = True

                ## Downslope retention index
##                gp.AddMessage("\nDEBUG: SKIPPING doing flow length!!!!")
##                raise Exception
            
                gp.FlowLength_sa(flowdir_channels, gwater_dret_flowlen, "DOWNSTREAM", gwater_comb_weight_ret)
                normalize(gwater_dret_flowlen, gwater_dret_index)

            gp.AddMessage("\n\tCreated Groundwater/Baseflow downslope retention index: " + gwater_dret_index)

            gp.AddMessage("\n\tCreating upslope source...")
            
            # Annual average precipitation index
            normalize(precip_annual, gwater_precip_annual_index)

            # Actual Evapotranspiration (AET) index
            normalize(AET, gwater_aet_index)

            # Soil depth index
            if not made_soil_depth_index:
                normalize(soil_depth, soil_depth_norm)
                gp.Minus_sa("1.0", soil_depth_norm, soil_depth_index)
                made_soil_depth_index = True
                
            # Combined weight source
            gp.SingleOutputMapAlgebra_sa("(" + gwater_precip_annual_index + " + (1 - " + gwater_aet_index + ") + " + \
                                         soil_texture + " + " + gwater_slope_index + " + (1 - " + flgw_index_cover + \
                                          ") + " + "(1 - " + flgw_index_rough + ") + " + soil_depth_index + ") / 7", gwater_comb_weight_source)

            ## Upslope source
##            gp.AddMessage("\nDEBUG: SKIPPING doing flow acc!!!!")
            gp.FlowAccumulation_sa(flow_dir, gwater_upslope_source, gwater_comb_weight_source)
            gp.AddMessage("\n\tCreated Groundwater/Baseflow upslope source: " + gwater_upslope_source)
        
        except:
            gp.AddError ("\nError processing Groundwater Recharge/Baseflow objective:  " + gp.GetMessages(2))
            raise Exception
 


    ### Write input parameters to an output file for user reference
    try:
        parameters.append("Script location: " + os.path.dirname(sys.argv[0]) + "\\" + os.path.basename(sys.argv[0]))
        gp.workspace = sys.argv[6]
        parafile = open(gp.workspace + "\\Output\\RIOS_Pre_Processing_" + now.strftime("%Y-%m-%d-%H-%M") + Suffix + ".txt", "w")
        parafile.writelines("RIOS PRE-PROCESSING PARAMETERS\n")
        parafile.writelines("______________________________\n\n")
        for para in parameters:
            parafile.writelines(para + "\n")
            parafile.writelines("\n")
        parafile.close()
    except:
        gp.AddError ("\nError creating parameter file:  " + gp.GetMessages(2))
        raise Exception


    ### Clean up temporary files
    gp.AddMessage("\nCleaning up temporary files...\n")
##    gp.AddMessage("\n!!!!! NOT CLEANING UP TEMPORARY FILES !!!!!...\n")
    try:
        gp.Delete_management(interws)
    except:
        gp.AddError("\nError cleaning up temporary files:  " + gp.GetMessages(2))
        raise Exception


except:
    gp.AddError ("\nError running script")
    raise Exception


