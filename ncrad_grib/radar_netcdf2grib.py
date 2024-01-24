#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Trasforma i netcdf delle cumulate stimate da radar in grib2.
In input viene gestito il formato netcdf definito dalle routine IDL.

Da modificare:
- gestione della variabile time perchè il netcdf sia convenzionale
- gestione delle cumulate in minuti

"""

import numpy as np
import argparse
import netCDF4

from datetime import datetime, timedelta
from eccodes import (
    codes_grib_new_from_samples,
    codes_set_key_vals,
    codes_set_values,
    codes_write,
    codes_release,
)

import warnings

warnings.filterwarnings("ignore")

# COSTANTI
rmiss_netcdf = "   -0.0100000"  # default dei netcdf
rmiss_grib = 9999
imiss = 255

tipo = "regular_ll"  # string
component_flag = 0  # int CONSTANT


def get_args():
    parser = argparse.ArgumentParser(
        description="Programma per la conversione dei file netcdf di cumulate radar in grib2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-i",
        "--input_file",
        dest="inputfile",
        required=True,
        help="File di input, required",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        dest="outputfile",
        required=False,
        help="File di output, optional",
    )

    args = parser.parse_args()

    return args


def radar_netcdf2grib(name_nc, fileout=None):

    try:
        # Apertura del file netcdf
        ncid = netCDF4.Dataset(name_nc)

        # Estraggo le dimensioni delle variabili immagazzinate
        dim_lon = ncid.dimensions["lon"].size
        dim_lat = ncid.dimensions["lat"].size
        mesh_xy = None

        # Estraggo l'istante di emissione del dato
        time = ncid.variables["time"].units
        """
        Time è definito come "hour before AAAA-MM-GG hh:mm:0"
        Nelle vecchie cumulate potrebbe esserci scritto "hours"
        invece di "hour" e "since" invece di "before". Per ovviare
        al problema divido la stringa in 4 sottostringhe.
        In questo modo la data è nella sottostringa 3 e l'ora
        nella sottostringa 4.
        """
        try:
            # Caso non CF-compliant
            time_to_read = time.split(" ")

            # Gestisco il caso in cui la cumulata sia "before" la data di validità.
            # In questo caso la variabile time sarà sempre zero, mentre la data di
            # validità sarà scritta nell'attributo "units".
            if "since" not in time_to_read:

                # se le units di time non sono CF-compliant, le correggo e
                # estraggo data_validita come datetime da num2date usando units ricorrette
                time_to_read[1] = "since"
                units_new = " ".join(time_to_read)
                cum_end = netCDF4.num2date(ncid.variables["time"][:], units_new, only_use_cftime_datetimes=False)[0]

            # Caso CF-compliant
            else:
                
                cum_end = netCDF4.num2date(ncid.variables["time"][:], time, only_use_cftime_datetimes=False)[0]

        except Exception: 
            print("Lettura time fallita")
        
        # Estraggo le variabili necessarie al grib
        for k in ncid.variables.keys():
            if k == "cum_pr_mm":  # Estraggo gli attributi del campo di pioggia
                varid_pr = ncid.variables["cum_pr_mm"]
                
                pr_units = varid_pr.units
                # Verifico che l'unità di misura sia 'mm':
                if pr_units.strip() != "mm" and pr_units.strip() != "kg m-2":
                    raise Exception("L'unità di misura non è mm, esco")

                # Gestisco il tempo di cumulazione
                acc_t = varid_pr.accum_time_h
                orig_acc_t = acc_t
                if acc_t == 0:
                    print("Accumulation time (acc_t) not defined! Default = 1.0 hour")
                    acc_t = 1.0
                elif acc_t > 0 and acc_t < 1.0:
                    # Sono cumulate su minuti: calcolo il tempo di cumulazione in minuti
                    acc_t = acc_t * 60
                    
                # Matrice precipitazione cumulata
                cum_pr_mm = [varid_pr[:]][0]
                # Sostituisco il valore mancante con rmiss
                cum_pr_mm = np.array(cum_pr_mm)
                cum_pr_mm = np.where(cum_pr_mm >= 0.0, cum_pr_mm, rmiss_grib)
                cum_pr_mm = cum_pr_mm[0]

            elif k == "geo_dim" or k == "geo_limits":
                try: 
                    varid_geo = ncid.variables["geo_dim"]
                except:
                    varid_geo = ncid.variables["geo_limits"]
                geo_lim = [varid_geo[:]][0]

            elif k == "mesh_dim" or k == "grid_mesh":
                try:
                    varid_mesh = ncid.variables["mesh_dim"]
                except:
                    varid_mesh = ncid.variables["grid_mesh"]
                mesh_xy = [varid_mesh[:]][0]

        if mesh_xy is None:
            raise Exception("Manca la variabile mesh_xy.")

        # Calcolo data inizio intervallo di cumulazione
        if time[0:7] == "minutes" or (orig_acc_t > 0 and orig_acc_t < 1.0):
            ind_unit_time = 0
            cum_begin = cum_end - timedelta(minutes=int(acc_t))
        else:
            ind_unit_time = 1
            cum_begin = cum_end - timedelta(hours=int(acc_t))

        """
        ==============================================================================
        SCRITTURA DEL GRIB
        ==============================================================================
        """
        if fileout is None:
            if time[0:7] == "minutes" or (orig_acc_t > 0 and orig_acc_t < 1.0):
                fileout = "radar_SRT_{}_{}min.grib2".format(
                    cum_end.strftime("%Y%m%d%H%M"), int(acc_t)
                )
            elif time[0:4] == "hour" or time[0:5] == "hours":
                fileout = "radar_SRT_{}_{}h.grib2".format(
                    cum_end.strftime("%Y%m%d%H%M"), int(acc_t)
                )

        print("Output file = {}".format(fileout))

        fout = open(fileout, "wb")

        # Definizione della griglia e del formato del grib  1 o 2
        gaid_template = codes_grib_new_from_samples("regular_ll_sfc_grib2")

        key_map_grib = {
            "generatingProcessIdentifier": 1,
            "centre": 80,  # 200
            "missingValue": rmiss_grib,
            "packingType": "grid_simple",
            "bitmapPresent": 1,
            "resolutionAndComponentFlags": 0,
            "topLevel": 0,  # l1
            "bottomLevel": imiss,  # l2
            "iDirectionIncrement": "MISSING",
            "jDirectionIncrement": "MISSING",
            "iDirectionIncrementInDegrees": mesh_xy[0],
            "jDirectionIncrementInDegrees": mesh_xy[1],
            "typeOfProcessedData": 2,  # [Analysis products]
            "typeOfStatisticalProcessing": 1,  # Accumulation
            "forecastTime": 0,
            # Istante di emissione del dato
            "dataDate": int(cum_begin.strftime("%Y%m%d")),
            "dataTime": int(cum_begin.strftime("%H%M")),
            "typeOfTimeIncrement": 1,  # 2
            "indicatorOfUnitOfTimeRange": ind_unit_time,  # 1=ore #0=minuti (Indicator of unit of time for time range over which statistical processing is done)
            "lengthOfTimeRange": int(
                acc_t
            ),  # Length of the time range over which statistical processing is done
            # 'indicatorOfUnitForTimeIncrement': 1, # (QUESTO DEVE ESSERE 255???)
            # 'timeIncrement': int(acc_t),          #Time increment between successive fields (QUESTO DEVE ESSERE 0????)
            "yearOfEndOfOverallTimeInterval": int(cum_end.strftime("%Y")),
            "monthOfEndOfOverallTimeInterval": int(cum_end.strftime("%m")),
            "dayOfEndOfOverallTimeInterval": int(cum_end.strftime("%d")),
            "hourOfEndOfOverallTimeInterval": int(cum_end.strftime("%H")),
            "minuteOfEndOfOverallTimeInterval": int(cum_end.strftime("%M")),
            "secondOfEndOfOverallTimeInterval": 0,
            # Variabile precipitazione
            "parameterCategory": 1,  # category
            "parameterNumber": 52,  # number
            "discipline": 0,  # discipline
            "shapeOfTheEarth": 1,  # shapeOfTheEarth
            "scaleFactorOfRadiusOfSphericalEarth": 2,  # scaleFactorOfRadiusOfSphericalEarth
            "scaledValueOfRadiusOfSphericalEarth": 637099700,  # scaledValueOfRadiusOfSphericalEarth
            "productDefinitionTemplateNumber": 8,
            "typeOfFirstFixedSurface": 1,
            "scaleFactorOfFirstFixedSurface": 0,
            "scaledValueOfFirstFixedSurface": 0,
        }

        codes_set_key_vals(gaid_template, key_map_grib)

        if ncid.Conventions == "CF-1.8":
            # "Geo limits [xLL, xUR, yLL, yUR]"
            loFirst = geo_lim[0]
            loLast = geo_lim[1]
            laFirst =  geo_lim[3]
            laLast = geo_lim[2]
        elif ncid.Conventions == "CF-1.4":
            # "Geo limits [yLL, xLL, yUR, xUR]"
            loFirst = geo_lim[1]
            loLast = geo_lim[3]
            laFirst = geo_lim[2]
            laLast = geo_lim[0]
            
        codes_set_key_vals(
            gaid_template,
            {
                "typeOfGrid": tipo,
                "Ni": dim_lon,  # nx
                "Nj": dim_lat,  # ny
                "longitudeOfFirstGridPointInDegrees": loFirst,
                "longitudeOfLastGridPointInDegrees": loLast,
                "latitudeOfFirstGridPointInDegrees": laFirst,  
                "latitudeOfLastGridPointInDegrees": laLast, 
                "uvRelativeToGrid": component_flag,  # component_flag
            },
        )

        cum_pr_mm = np.flip(cum_pr_mm, 0)
        codes_set_values(gaid_template, cum_pr_mm.flatten())

        codes_write(gaid_template, fout)
        codes_release(gaid_template)
        fout.close()

        # Chiusura file netcdf
        ncid.close()

    except OSError:
        print("Cannot open {}".format(name_nc))
        print("Probabile file mancante.")


def main():
    args = get_args()

    inputfile = args.inputfile
    if args.outputfile:
        outputfile = args.outputfile
    else:
        outputfile = None

    radar_netcdf2grib(inputfile, outputfile)


if __name__ == "__main__":
    main()
