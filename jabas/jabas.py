# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 21:13:48 2019

@author: Ronald Castillo Capino
"""
from doopl.factory import *
import pandas as pd
import numpy as np
from os.path import dirname, abspath, join

DATADIR=dirname(abspath('__file__'))
mod=join(DATADIR,"Jabas2.mod")
data=join(DATADIR,"Jabas.xlsx")
xl = pd.ExcelFile(data)
parametros=xl.parse("parametros")
Jabas=xl.parse("Jabas")
Jabas=Jabas[['Codigo de Producto','Peso de jaba [kg]','Alto por jabas [m]','Demanda de productos']].astype(float)
Jabas['Codigo de Producto']=Jabas['Codigo de Producto'].astype(int).astype(str)
Jabas['Demanda de productos']=Jabas['Demanda de productos'].astype(int)
with create_opl_model(model=mod) as opl:
    opl.set_input("parametros",parametros)    
    opl.set_input("jabaInformacion",Jabas)
    opl.run()
    jabaOutput=opl.get_table("jabasNPallet")
    palletsOutput=opl.get_table("PalletInfo")
jabaOutput.to_excel("Jabas1.xlsx",sheet_name='ResultadosJabas',index=False)
palletsOutput.to_excel("Jabas2.xlsx",sheet_name='ResultadosPallet',index=False)