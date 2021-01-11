from datetime import datetime
today = datetime.now()
today = today.strftime("%d_%m_%Y")
import logging
logging.basicConfig(format='%(asctime)s: %(message)s',filename='log_info_'+today+'.log',filemode='a',level=logging.INFO,datefmt='%Y-%m-%d %H:%M:%S')

from doopl.factory import *

import pandas
import os
import sys
from os.path import dirname, abspath, join
import pdb
import numpy
import scipy
import time
import itertools
import time
import math
from multiprocessing import Process, Queue, current_process, freeze_support, Pool

if sys.platform.startswith('win'):
	sys.path.append(os.path.relpath("..\\utilities"))
else:
	sys.path.append(os.path.relpath("../utilities"))
	
import util
import hamiltonian
#CAMBIA A CreacionPallets
relPathToOPL = "..\\CreacionPallets\\"
if not sys.platform.startswith('win'):
	relPathToOPL = "../CreacionPallets/"
	
relPathToParam = "..\\Parametros\\"
if not sys.platform.startswith('win'):
	relPathToParam = "../Parametros/"

#Creacion de una solución inicial de pallets para ingresar como patrones iniciales del problema maestro
def crearInicial(info, Resistance, MAXVOLUME, MAXPESO, PALLETCOST):
	Resistance = Resistance.set_index('RESISTENCIA')
	index_resist = Resistance.index
	patterns = pandas.DataFrame(columns=['ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD'])
	patternCost = pandas.DataFrame(columns=['ID_PALLET','COSTO'])
	pattern = 0
	
	for cont in info.CONTAMINANTE.unique():
		contaminanteDF = info[info.CONTAMINANTE==cont]
		
		for i in contaminanteDF.PASILLO.unique():
			pasilloDF = contaminanteDF[contaminanteDF.PASILLO == i].sort_values(['RESISTENCIA'],ascending = False).reset_index(drop=True)
			pasilloDF['checked'] = False
			for idx, row in pasilloDF.iterrows():
				#print(row[1])
				maxUnits = int(min(MAXPESO/row.PESO,Resistance.loc[row.RESISTENCIA,'maxPeso'] / row.PESO, MAXVOLUME / row.VOLUMEN, row.CANTIDAD))
				if maxUnits == int(Resistance.loc[row.RESISTENCIA,'maxPeso'] / row.PESO) or maxUnits == int(MAXVOLUME / row.VOLUMEN) or maxUnits == int(MAXPESO / row.PESO):
					patterns = patterns.append(pandas.DataFrame({'ID_PALLET':[pattern],'CODIGOARTICULO':[row.CODIGOARTICULO],'CODIGOUNIDADMANEJO':[row.CODIGOUNIDADMANEJO],'CANTIDAD':[maxUnits]}))
					costo = PALLETCOST * 2
					patternCost = patternCost.append(pandas.DataFrame({'ID_PALLET':[pattern],'COSTO':[costo]}))
					pattern += 1
					pasilloDF.loc[idx,'checked'] = True
					
			num_iter = 0
			while pasilloDF[pasilloDF.checked==False]['checked'].count()>0 and num_iter<3:
				#CAMBIO!!
				pesoResistencia = pandas.DataFrame({'resistencia':index_resist,'peso':0})
				peso = 0
				volumen = 0
				#index = 0
				for idx, row in pasilloDF.iterrows():
					if row.checked == False:
						pesoR = pesoResistencia.loc[row.RESISTENCIA,'peso'] + row.CANTIDAD * row.PESO
						pesoT = peso + row.CANTIDAD * row.PESO
						vol = volumen + row.CANTIDAD * row.VOLUMEN
						if pesoT < MAXPESO and vol < MAXVOLUME and pesoR <= Resistance.loc[row.RESISTENCIA,'maxPeso']:
							pesoResistencia.loc[row.RESISTENCIA,'peso'] = pesoR
							peso = pesoT
							volumen = vol
							pasilloDF.loc[idx,'checked'] = True
							nuevo = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'CODIGOARTICULO':[row.CODIGOARTICULO],'CODIGOUNIDADMANEJO':[row.CODIGOUNIDADMANEJO],'CANTIDAD':[row .CANTIDAD]})
							patterns = patterns.append(nuevo)
							num_iter =0

				costo = PALLETCOST * 500
				nuevoCosto = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'COSTO':[costo]})
				patternCost = patternCost.append(nuevoCosto)
				pattern = pattern + 1
				num_iter = num_iter + 1
				if num_iter > 2:
					print('Un artículo no ha podido ser agregado a la inicializacion')
			
			if pasilloDF[pasilloDF.checked==False]['checked'].count() > 0:
				for idx, row in pasilloDF[pasilloDF.checked==False].iterrows():
					pasilloDF.loc[idx,'checked'] = True
					nuevo = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'CODIGOARTICULO':[row.CODIGOARTICULO],'CODIGOUNIDADMANEJO':[row.CODIGOUNIDADMANEJO],'CANTIDAD':[row .CANTIDAD]})
					patterns = patterns.append(nuevo)						

	patterns = patterns.reset_index(drop=True)
	patternCost = patternCost.reset_index(drop=True)
	return patterns, patternCost

#Ejecucion del modelo maestro en su version relajada (variables continuas)
#Elección de la combinación de pallets a utilizar para cubrir la demanda
def oplMasterRelajado(mod, parametros, patterns, patternCost):
	duales = pandas.DataFrame()
	with create_opl_model(model=mod) as opl:
		opl.mute()
		opl.set_input('info_articulos', parametros[['CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','PESO','VOLUMEN','CONTAMINANTE','X_PASILLO_LOCAL','COORDENADAYLOCAL']])
		opl.set_input('patterns', patterns)
		opl.set_input('patternCost', patternCost)
		opl.setExportExternalData('Master_nave.dat')

		if opl.run():
			curr = opl.objective_value
			#print("OBJECTIVE MASTER: " + str(curr))
			duales = opl.get_table('fillDuals')
			Reporte=opl.report
			opl.end()
		else:
			print("No solution Master!")
			opl.end()
			
	return curr, duales

#Ejecucion del modelo auxiliar
#Creación de pallets a partir de un incentivo definido por los valores duales
def oplAuxliar(mod, parametros, info_articulos, duales, resistencia, numPallet):
	nuevo = pandas.DataFrame()
	nuevoCosto = pandas.DataFrame()
	#AQUI VOY
	with create_opl_model(model=mod) as oplAux:
		oplAux.mute()
		oplAux.set_input('parametros', parametros)
		oplAux.set_input('info_articulos', info_articulos[['CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','VOLUMEN','PESO','X_PASILLO_LOCAL', 'COORDENADAYLOCAL','RESISTENCIA','PASILLO','CONTAMINANTE']])
		oplAux.set_input('infoDuals', duales)
		oplAux.set_input('infoResistances', resistencia[['RESISTENCIA', 'maxPeso', 'maxVolumen', 'maxPesoEncima']])
		name = 'Aux_nave.dat'
		oplAux.setExportExternalData(name)
		if oplAux.run():
			sol = oplAux.objective_value
			#print("OBJECTIVE AUX: " + str(sol))
			#print(oplAux.report)

			#METER NUEVOS PATRONES
			if sol<0.01:
				nuevo = oplAux.get_table('contentsFinal')
				nuevo.insert(0,'ID_PALLET',numPallet+1)
				nuevo.columns=['ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD']
				
				nuevoCosto = oplAux.get_table('costPallet')
				nuevoCosto.columns=['ID_PALLET','COSTO']
				nuevoCosto.loc[0,'ID_PALLET']=numPallet+1
				oplAux.end()
		else:
			print("No solution Aux!")
			oplAux.end()
				
	return nuevo, nuevoCosto

#Ejecucion del modelo maestro en su version entera (variables enteras)
#Elección de la combinación de pallets a utilizar para cubrir la demanda
def oplMasterINT(mod, info_articulos, patterns, patternCost, nave):
	contenido = pandas.DataFrame()
	resumen = pandas.DataFrame()
	with create_opl_model(model=mod) as oplINT:
		oplINT.mute()
		oplINT.set_input('info_articulos', info_articulos[['CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','PESO','VOLUMEN','CONTAMINANTE','X_PASILLO_LOCAL','COORDENADAYLOCAL']])
		oplINT.set_input('patterns', patterns)
		oplINT.set_input('patternCost', patternCost)
		oplINT.setExportExternalData('MasterINT_nave'+str(nave)+'.dat')
		if oplINT.run():
			FUN_OBJ = oplINT.objective_value
			#print("OBJECTIVE MASTER INTEGER: " + str(FUN_OBJ))
			Solucion=oplINT.report
			oplINT.end()
		else:
			print("No solution Master int!")
			oplINT.end()

	contenido = Solucion['contentsFinal']
	resumen = Solucion['Tareas']

	return contenido, resumen

#Ejecucion del modelo de agrupacion de tareas de una misma nave con capacidad disponible
#Toma las tareas no completas y une aquellas que aun tengan disponibilidad
def oplAgregar(mod, parametros, info_articulos, infoResistencia, subpallets, contents, infoPeso, infoVol):
	tareas = []
	unionPallets = []
	with create_opl_model(model=mod) as opl:
		opl.mute()
		opl.set_input('parametros', parametros)
		opl.set_input('info_articulos', info_articulos[['CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','VOLUMEN','PESO','X_PASILLO_LOCAL','COORDENADAYLOCAL','RESISTENCIA','PASILLO','CONTAMINANTE']])
		opl.set_input('infoResistances', infoResistencia[['RESISTENCIA', 'maxPeso', 'maxVolumen', 'maxPesoEncima']])
		opl.set_input('subpallets', subpallets)
		#opl.set_input('contents', contents)
		opl.set_input('infoPeso', infoPeso)
		opl.set_input('infoVolumen', infoVol)
		opl.setExportExternalData('infoAgrupar.dat')
		if opl.run():
			FO = opl.objective_value
			Solucion=opl.report
			tareas = Solucion['Tareas']
			unionPallets = Solucion['unionPallets']
		else:
			print("No solution agrupar!")
		
	return tareas, unionPallets

#Ejecucion del modelo de agrupacion de tareas entre diferentes naves con capacidad disponible
#Toma las tareas no completas y une aquellas que aun tengan disponibilidad entre las naves
def oplAgregarNaves(mod, parametros, info_articulos, infoResistencia, subpallets, contents, infoPeso, infoVol):
	tareas = []
	unionPallets = []
	if len(subpallets) > 0:
		with create_opl_model(model=mod) as opl:
			opl.mute()
			opl.set_input('parametros', parametros)
			opl.set_input('info_articulos', info_articulos[['CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','VOLUMEN','PESO','X_PASILLO_LOCAL','COORDENADAYLOCAL','RESISTENCIA','PASILLO','CONTAMINANTE']])
			opl.set_input('infoResistances', infoResistencia[['RESISTENCIA', 'maxPeso', 'maxVolumen', 'maxPesoEncima']])
			opl.set_input('subpallets', subpallets)
			opl.set_input('infoPeso', infoPeso)
			opl.set_input('infoVolumen', infoVol)
			opl.setExportExternalData('infoAgruparNaves.dat')
			if opl.run():
				FO = opl.objective_value
				Solucion=opl.report
				tareas = Solucion['Tareas']
				unionPallets = Solucion['unionPallets']
			else:
				print("No solution agrupar Naves!")
		
	return tareas, unionPallets

#Definicion de valores duales para incentivar la creacion de tareas para pallets completos
def definirDuales(demandaFaltante, duales, newPattern):
	actualizar = demandaFaltante.merge(newPattern[['CODIGOARTICULO','CANTIDAD']], left_on = ['CODIGOARTICULO'], right_on = ['CODIGOARTICULO'], how = 'left').fillna(0)
	actualizar.insert(len(actualizar.keys()),'ACTUAL',actualizar.CANTIDAD_x-actualizar.CANTIDAD_y)
	nuevo_dual = actualizar[['CODIGOARTICULO','ACTUAL']].merge(duales, left_on = ['CODIGOARTICULO'], right_on = ['CODIGOARTICULO'], how = 'left')
	nuevo_dual['DUAL']= numpy.where(nuevo_dual['dualValue']>0,nuevo_dual.dualValue,nuevo_dual.ACTUAL)
	nuevo_dual = nuevo_dual[['CODIGOARTICULO','DUAL']]
	
	return demandaFaltante, nuevo_dual

#Eliminacion de producto que exceda la demanda 
def eliminarExcesos(contenido, resumen, info):
	numPallet = 0
	pallets = pandas.DataFrame()
	resumenPallets = pandas.DataFrame()
	#Expandir los pallets repetidos (quantityCuts > 1)
	for idx,row in resumen.iterrows():
		contenidoPallet = contenido[contenido.ID_PALLET == row.ID_PALLET][['CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD']]
		contenidoPallet.insert(loc=0, column='ID_PALLET', value =0)
		if row.quantityCuts > 1:
			for j in range(1,int(row.quantityCuts)+1):
				temp = contenidoPallet.copy()
				temp.loc[:,'ID_PALLET'] = numPallet
				pallets = pallets.append(temp)
				resumenPallets = resumenPallets.append(pandas.DataFrame.from_dict({'ID_PALLET':[numPallet],'PESO':[row.PESO],'VOLUMEN':[row.VOLUMEN]}))
				numPallet += 1
		else:
			temp = contenidoPallet.copy()
			temp.loc[:,'ID_PALLET'] = numPallet
			pallets = pallets.append(temp)
			resumenPallets = resumenPallets.append(pandas.DataFrame.from_dict({'ID_PALLET':[numPallet],'PESO':[row.PESO],'VOLUMEN':[row.VOLUMEN]}))
			numPallet += 1
	pallets = pallets.reset_index(drop=True)
	resumenPallets = resumenPallets.reset_index(drop=True)
	#Eliminar exceso
	resumenPallets = resumenPallets.sort_values(['PESO','VOLUMEN']).set_index('ID_PALLET')
	empacado = pallets.groupby(['CODIGOARTICULO'], as_index=False).CANTIDAD.sum().sort_values('CANTIDAD').reset_index(drop=True).set_index('CODIGOARTICULO')
	
	for idx,row in info.iterrows():
		barcode = row.CODIGOARTICULO
		demanda = row.CANTIDAD
		dif = empacado.loc[barcode,'CANTIDAD'] - demanda
		if dif > 0:
			tempPallet = pallets[pallets.CODIGOARTICULO == barcode][['ID_PALLET','CANTIDAD']].sort_values('CANTIDAD')
			for idx1,row1 in tempPallet.iterrows():
				if dif < row1.CANTIDAD:
					pallets.loc[idx1,'CANTIDAD'] = pallets.loc[idx1,'CANTIDAD'] - dif
					resumenPallets.loc[row1.ID_PALLET,'PESO'] = resumenPallets.loc[row1.ID_PALLET,'PESO'] - dif * row.PESO
					resumenPallets.loc[row1.ID_PALLET,'VOLUMEN'] = resumenPallets.loc[row1.ID_PALLET,'VOLUMEN'] - dif * row.VOLUMEN
					dif = 0
				elif dif >= row1.CANTIDAD:
					dif = dif - pallets.loc[idx1,'CANTIDAD']
					resumenPallets.loc[row1.ID_PALLET,'PESO'] = resumenPallets.loc[row1.ID_PALLET,'PESO'] - pallets.loc[idx1,'CANTIDAD'] * row.PESO
					resumenPallets.loc[row1.ID_PALLET,'VOLUMEN'] = resumenPallets.loc[row1.ID_PALLET,'VOLUMEN'] - pallets.loc[idx1,'CANTIDAD'] * row.VOLUMEN
					pallets.loc[idx1,'CANTIDAD'] = 0
	
	tempTotal = pallets.copy()
	for idx, row in tempTotal.iterrows():
		if row.CANTIDAD == 0:
			pallets = pallets.drop(idx)
	
	id_pallets_filtro = pallets.ID_PALLET.unique()
	resumenPallets = resumenPallets.reset_index()
	resumenPallets = resumenPallets[resumenPallets.ID_PALLET.isin(id_pallets_filtro)]
	return resumenPallets, pallets

#Definicion de tareas que pueden ser reprocesadas - tareas que tienen capacidad para ser agrupadas con una otra	
def definicionSubpallets(parametros, resistencias, info_articulos, resumenPallets, pallets):
	agrupar = []
	completos = []
	numPallets = 0
	subpallets = [] 
	content = []
	infoPeso = []
	infoVol = []
	info_agrupar=info_articulos
	
	maxPeso_lego = parametros.loc[parametros[parametros.PARAMETER=='MAXWEIGHT'].index[0],'VALUE']
	maxVol_lego = parametros.loc[parametros[parametros.PARAMETER=='MAXVOLUME'].index[0],'VALUE']
	porcentaje = 0.8
	
	for idx,row in resumenPallets.iterrows():
		if row.VOLUMEN < maxVol_lego*porcentaje and row.PESO < maxPeso_lego*porcentaje:
			agrupar.append(int(row.ID_PALLET))
		else:
			completos.append(int(row.ID_PALLET))
	
	if len(agrupar) > 0:
		numPallets = len(agrupar)
		
		#info base (pallet cost, dist cost, maxW, maxV, numPallet)
		indice = parametros[parametros.PARAMETER=='NUMPALLETS'].index[0]
		parametros.at[indice,'VALUE'] = len(resumenPallets)
		
		#parametros (barcode,u_manejo,demand,volume,weight,x,y,resistance,pasillo,contamination)
		info_agrupar = info_articulos[info_articulos.CODIGOARTICULO.isin(pallets.CODIGOARTICULO.unique())][['CODIGOARTICULO','CODIGOUNIDADMANEJO','PESO','VOLUMEN','RESISTENCIA','CONTAMINANTE','UBICACION','NAVE','PASILLO','RACK','X_PASILLO_LOCAL','COORDENADAYLOCAL']]
		demanda = pallets.copy().groupby(['CODIGOARTICULO'], as_index=False).CANTIDAD.sum()
		#sujeto a cambios en los nombres de tablas
		demanda.columns = (['CODIGOARTICULO','CANTIDAD'])
		info_agrupar = info_agrupar.merge(demanda, left_on = ['CODIGOARTICULO'], right_on = ['CODIGOARTICULO'])

		pallet_info = pallets.merge(info_agrupar, left_on=['CODIGOARTICULO'], right_on=['CODIGOARTICULO'], how='left')
		
		subpallets = pandas.DataFrame()
		content = pandas.DataFrame()
		infoPeso = pandas.DataFrame()
		infoVol = pandas.DataFrame()
		
		for id in agrupar:
			pesoGlobal = 0
			volGlobal = 0
			tempResistencia = pallet_info[pallet_info.ID_PALLET==id]
			#DEFINIR MEJOR CONTAMINACION
			cont_actual = ['CONTAMINANTE','CONTAMINABLE']
			conta = tempResistencia.CONTAMINANTE.unique()
			conta = numpy.array(list(filter(lambda x: x in cont_actual, conta)))
			if len(conta)>0:
				conta = conta[0]
			else:
				conta = 'RESISTENTE A CONTAMINACION'
			#CAMBIO A RESISTENCIA VARIABLE
			content = content.append(tempResistencia[['ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO_x','CANTIDAD_x']])
			tempResistencia.insert(loc=len(tempResistencia.keys()),column='prodPeso',value=tempResistencia.PESO*tempResistencia.CANTIDAD_x)
			tempResistencia.insert(loc=len(tempResistencia.keys()),column='prodVol',value=tempResistencia.VOLUMEN*tempResistencia.CANTIDAD_x)
			
			for r in resistencias.copy().RESISTENCIA:
				peso = tempResistencia[tempResistencia.RESISTENCIA == r].prodPeso.sum()
				infoPeso = infoPeso.append(pandas.DataFrame({'id':[id],'resistencia':[r],'PESO':[peso]}))
				pesoGlobal = pesoGlobal + peso
				volumen = tempResistencia[tempResistencia.RESISTENCIA == r].prodVol.sum()
				infoVol = infoVol.append(pandas.DataFrame({'id':[id],'resistencia':[r],'VOLUMEN':[volumen]}))
				volGlobal = volGlobal + volumen
			
			minx = tempResistencia.X_PASILLO_LOCAL.min()
			maxx = tempResistencia.X_PASILLO_LOCAL.max()
			miny = tempResistencia.COORDENADAYLOCAL.min()
			maxy = tempResistencia.COORDENADAYLOCAL.max()
			subpallets = subpallets.append(pandas.DataFrame.from_dict({'id':[id],'VOLUMEN':[volGlobal],'PESO':[pesoGlobal],'contaminacion':[conta],'minX':[minx],'maxX':[maxx],'minY':[miny],'maxY':[maxy]}))
		
	return completos, numPallets, subpallets, content, infoPeso, infoVol, info_agrupar

#Definicion de tareas que pueden ser reprocesadas - tareas que tienen capacidad para ser agrupadas con una otra	
def definicionSubpalletNaves(parametros, resistencias, info_articulos, resumenPallets, pallets):
	agrupar = []
	completos = []
	numPallets = 0
	subpallets = []
	content = []
	infoPeso = []
	infoVol = []
	pesoGlobal = 0
	volGlobal = 0
	info_agrupar=info_articulos
	
	maxPeso_lego = parametros.loc[parametros[parametros.PARAMETER=='MAXWEIGHT_FUR'].index[0],'VALUE']
	maxVol_lego = parametros.loc[parametros[parametros.PARAMETER=='MAXVOLUME_FUR'].index[0],'VALUE']
	porcentaje = 0.8	
	
	if len(resumenPallets) > 0:
		for idx,row in resumenPallets.iterrows():
			if row.VOLUMEN < maxVol_lego*porcentaje and row.PESO < maxPeso_lego*porcentaje:
				agrupar.append(int(row.ID_PALLET))
			else:
				completos.append(int(row.ID_PALLET))
		
		pallets = pallets[pallets.ID_PALLET.isin(agrupar)]
		if len(agrupar) > 0:
			numPallets = len(agrupar)
			
			indice = parametros[parametros.PARAMETER=='NUMPALLETS'].index[0]
			parametros.at[indice,'VALUE'] = len(resumenPallets)
			
			info_agrupar = info_articulos[info_articulos.CODIGOARTICULO.isin(pallets.CODIGOARTICULO.unique())][['CODIGOARTICULO','CODIGOUNIDADMANEJO','PESO','VOLUMEN','RESISTENCIA','CONTAMINANTE','UBICACION','NAVE','PASILLO','RACK','X_PASILLO_LOCAL','COORDENADAYLOCAL']]
			demanda = pallets.copy().groupby(['CODIGOARTICULO'], as_index=False).CANTIDAD.sum()
			demanda.columns = (['CODIGOARTICULO','CANTIDAD'])
			info_agrupar = info_agrupar.merge(demanda, left_on = ['CODIGOARTICULO'], right_on = ['CODIGOARTICULO'])

			pasillos = pandas.DataFrame.from_dict(info_agrupar.PASILLO.unique()).reset_index()
			pallet_info = pallets.merge(info_agrupar, left_on=['CODIGOARTICULO'], right_on=['CODIGOARTICULO'], how='left')
			
			subpallets = pandas.DataFrame()
			content = pandas.DataFrame()
			infoPeso = pandas.DataFrame()
			infoVol = pandas.DataFrame()
			
			for id in agrupar:
				pesoGlobal = 0
				volGlobal = 0
				tempResistencia = pallet_info[pallet_info.ID_PALLET==id]
				#DEFINIR MEJOR CONTAMINACION
				cont_actual = ['CONTAMINANTE','CONTAMINABLE']
				conta = tempResistencia.CONTAMINANTE.unique()
				conta = numpy.array(list(filter(lambda x: x in cont_actual, conta)))
				if len(conta)>0:
					conta = conta[0]
				else:
					conta = 'RESISTENTE A CONTAMINACION'
				#CAMBIAR A RESISTENCIA VARIABLE
				content = content.append(tempResistencia[['ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO_x','CANTIDAD_x']])
				tempResistencia.insert(loc=len(tempResistencia.keys()),column='prodPeso',value=tempResistencia.PESO*tempResistencia.CANTIDAD_x)
				tempResistencia.insert(loc=len(tempResistencia.keys()),column='prodVol',value=tempResistencia.VOLUMEN*tempResistencia.CANTIDAD_x)
				
				for r in resistencias.copy().RESISTENCIA:
					peso = tempResistencia[tempResistencia.RESISTENCIA == r].prodPeso.sum()
					infoPeso = infoPeso.append(pandas.DataFrame({'id':[id],'resistencia':[r],'PESO':[peso]}))
					pesoGlobal = pesoGlobal + peso
					volumen = tempResistencia[tempResistencia.RESISTENCIA == r].prodVol.sum()
					infoVol = infoVol.append(pandas.DataFrame({'id':[id],'resistencia':[r],'VOLUMEN':[volumen]}))
					volGlobal = volGlobal + volumen
				
				minx = tempResistencia.X_PASILLO_LOCAL.min()
				maxx = tempResistencia.X_PASILLO_LOCAL.max()
				miny = tempResistencia.COORDENADAYLOCAL.min()
				maxy = tempResistencia.COORDENADAYLOCAL.max()
				subpallets = subpallets.append(pandas.DataFrame.from_dict({'id':[id],'VOLUMEN':[volGlobal],'PESO':[pesoGlobal],'contaminacion':[conta],'minX':[minx],'maxX':[maxx],'minY':[miny],'maxY':[maxy]}))

	return completos, numPallets, subpallets, content, infoPeso, infoVol, info_agrupar

#Asignación de pallet padre - hijo 
def crearPalletLegos(pallet_agrupado, agrupacion, tareas_despacho, resumen_despacho, desp, contador):
	
	pallet_agrupado = pallet_agrupado.reset_index(drop=True)
	agrupacion = agrupacion.reset_index(drop=True)
	tareas_despacho = tareas_despacho.reset_index(drop=True)
	resumen_despacho = resumen_despacho.reset_index(drop=True)
	
	conteo = agrupacion.groupby(['pallet'], as_index=False).subpallet.count()
	full_pallet=conteo[conteo.subpallet>1]['pallet']
	if type(full_pallet) == pandas.core.series.Series:
		full_pallet = full_pallet.to_frame()
	full_pallet.insert(0,'nuevo_id',numpy.arange(len(full_pallet)))
	full_pallet.insert(0,'PALLET_IDX',full_pallet.nuevo_id+contador)
	legos = agrupacion[agrupacion.pallet.isin(full_pallet.pallet)].reset_index(drop=True)
	legos = legos.merge(full_pallet[['pallet','PALLET_IDX']], left_on = ['pallet'], right_on=['pallet'], how = 'left')
	info_full_pallet = pallet_agrupado[pallet_agrupado.ID_PALLET.isin(full_pallet.pallet)]
	info_full_pallet = info_full_pallet.merge(full_pallet[['pallet','PALLET_IDX']], left_on = ['ID_PALLET'], right_on = ['pallet'])
	info_full_pallet = info_full_pallet[['PALLET_IDX','PESO','VOLUMEN']]
	info_full_pallet.insert(0,'NAVE',0)
	info_full_pallet.insert(0,'CODIGODESPACHO',desp)
	
	tarea_legos = tareas_despacho[tareas_despacho.ID_PALLET.isin(legos.subpallet)].reset_index(drop=True)
	tarea_legos = tarea_legos.rename(columns={'ID_PALLET':'LEGO_IDX'})
	tareas_legos = tarea_legos.merge(legos[['subpallet','PALLET_IDX','base']], left_on=['LEGO_IDX'], right_on=['subpallet'])
	tareas_legos = tareas_legos.rename(columns={'base':'BASE'})
	tareas_legos = tareas_legos[['CODIGODESPACHO','NAVE','PALLET_IDX','LEGO_IDX','CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','PASILLO','RACK','BASE']]
	#DROP DE LOS LEGOS 
	tareas_pallets = tareas_despacho.drop(tareas_despacho[tareas_despacho.ID_PALLET.isin(legos.subpallet)].index)
	tareas_pallets = tareas_pallets.rename(columns={'ID_PALLET':'PALLET_IDX'})
	tareas_pallets.insert(len(tareas_pallets.keys()),'BASE',1)
	resumen_tareas = resumen_despacho.copy()
	resumen_tareas = resumen_tareas.rename(columns={'ID_PALLET':'TAREA_IDX'})
	resumen_pallets = resumen_despacho.drop(resumen_despacho[resumen_despacho.ID_PALLET.isin(legos.subpallet)].index)
	resumen_pallets = resumen_pallets.rename(columns={'ID_PALLET':'PALLET_IDX'})
	resumen_pallets = resumen_pallets.append(info_full_pallet)
	
	if len(full_pallet) > 0:
		contador = full_pallet.PALLET_IDX.max() + 1
	
	return tareas_legos, tareas_pallets, resumen_tareas, resumen_pallets, contador

#Calculo de distancias y creacion de tabla de resumen
def getMetrics(pallets,legos,codigodespacho,distances,parametros,verificados):
	#for each pallet or lego, determine the weight, volume, bultos, route, minimum resistance, and distance.
	#if a lego/pallet has at least maxWeight and there is only one or none legos 
	tmpPallets = pallets[pallets.CODIGODESPACHO == codigodespacho]
	tmpLegos = legos[legos.CODIGODESPACHO == codigodespacho]
	palletIdxs = (set(tmpPallets.PALLET_IDX.unique())).union(set(tmpLegos.PALLET_IDX.unique()))
	numPallets = len(palletIdxs)
	numCompletePallets = len(tmpPallets.PALLET_IDX.unique())
	tempDF = hamiltonian.createTareaInfo(tmpPallets,verificados)
	gb = tempDF.groupby(by=['PALLET_IDX']).agg({'pesoAsignado': sum, 'volumenAsignado': sum, 'NAVE': min, 'ASIGNADO': sum, 'RESISTENCIA': min}).reset_index()
	gb.insert(1,'LEGO_IDX','')
	tempDF = hamiltonian.createTareaInfo(tmpLegos,verificados)
	gb = gb.append(tempDF.groupby(by=['PALLET_IDX','LEGO_IDX']).agg({'pesoAsignado': sum, 'volumenAsignado': sum, 'NAVE': min, 'ASIGNADO': sum, 'RESISTENCIA': min}).reset_index(),ignore_index = True)
	#determine bultos estibados. consider legos for full pallets, legos in a pallet that has a base lego, but the lego is not the base lego, and the legos in a pallet
	#that do not have the highest resistencia.
	bultosEstibados = 0.
	#find the legos that complete the full pallets
	bultosEstibados = bultosEstibados + tmpLegos[tmpLegos.PALLET_IDX.isin(tmpPallets.PALLET_IDX.unique())].ASIGNADO.sum()
	gb = gb.groupby(by=['PALLET_IDX','LEGO_IDX']).agg({'pesoAsignado': sum, 'volumenAsignado': sum, 'NAVE': min, 'ASIGNADO': sum, 'RESISTENCIA': min}).reset_index()
	#por pallet: peso, bultos, num legos/componentes, volumen, estibaje
	palletMetrics = pandas.DataFrame(data=None, columns = ['PALLET_IDX','LEGO_IDX','metric','value'])
	for palletIdx in palletIdxs:
		componentes = 0
		if palletIdx in tmpPallets.PALLET_IDX.unique():
			componentes = componentes + 1
		componentes = componentes + len(tmpLegos[tmpLegos.PALLET_IDX==palletIdx].LEGO_IDX.unique())
		if palletIdx in tmpPallets.PALLET_IDX.unique():
			palletMetrics.loc[len(palletMetrics)] = [palletIdx,'','componentes',componentes]
		if palletIdx in tmpLegos.PALLET_IDX.unique():
			for legoIdx in tmpLegos[tmpLegos.PALLET_IDX==palletIdx].LEGO_IDX.unique():
				palletMetrics.loc[len(palletMetrics)] = [palletIdx,legoIdx,'componentes',componentes]
	gb.columns = ['PALLET_IDX','LEGO_IDX','peso','volumen','nave','bultos','resistencia']
	for metric in ['peso','volumen','bultos']:
		gb['metric'] = metric
		gb['value'] = gb[metric]
		palletMetrics = palletMetrics.append(gb[['PALLET_IDX','LEGO_IDX','metric','value']], ignore_index = True)

	#for every pallet and lego, get the distance
	for palletIdx in palletIdxs:
		totalDistance = 0
		#TODO: get individual distances and routes to include in the legos and pallets
		rutaPallet = tmpPallets[tmpPallets.PALLET_IDX == palletIdx][['CODIGODESPACHO','CB','NAVE','PALLET_IDX','ASIGNADO']].copy()
		if len(rutaPallet) > 0:
			nave = rutaPallet.NAVE.values[0]
			distance, ruta = hamiltonian.getHamiltonianDistance(rutaPallet,verificados,distances[nave],parametros)
			totalDistance = totalDistance + distance
			pallets = hamiltonian.addRuta(pallets,rutaPallet,ruta)
			palletMetrics.loc[len(palletMetrics)] = [palletIdx,'','distancia',totalDistance]
		for legoIdx in tmpLegos[tmpLegos.PALLET_IDX == palletIdx].LEGO_IDX.unique():
			totalDistance = 0
			rutaLego = tmpLegos[(tmpLegos.PALLET_IDX == palletIdx) & (tmpLegos.LEGO_IDX == legoIdx)][['CODIGODESPACHO','CB','NAVE','LEGO_IDX','ASIGNADO']].copy()
			if len(rutaLego) > 0:
				nave = rutaLego.NAVE.values[0]
				distance, ruta = hamiltonian.getHamiltonianDistance(rutaLego,verificados,distances[nave],parametros)
				legos = hamiltonian.addRuta(legos,rutaLego,ruta)
				totalDistance = totalDistance + distance
				palletMetrics.loc[len(palletMetrics)] = [palletIdx,legoIdx,'distancia',totalDistance]
	return palletMetrics, pallets, legos		
	#por lego/componente: distancia 

#Generacion de rutas de recoleccion	
def generarPicking(pallets,legos,codigodespacho,distances,parametros,verificados):
	#full pallets
	pallets_tsp =  pallets[['CODIGODESPACHO','NAVE','PALLET_IDX','CODIGOARTICULO','CANTIDAD','BASE']].copy()
	pallets_tsp = pallets_tsp.rename(columns={'CODIGOARTICULO':'CB'})
	pallets_tsp = pallets_tsp.rename(columns={'CANTIDAD':'ASIGNADO'})
	pallets_tsp.insert(len(pallets_tsp.keys()),'ORDEN',0)
	
	legos_tsp = legos[['CODIGODESPACHO','NAVE','PALLET_IDX','LEGO_IDX','CODIGOARTICULO','CANTIDAD','BASE']].copy()
	legos_tsp = legos_tsp.rename(columns={'CODIGOARTICULO':'CB'})
	legos_tsp = legos_tsp.rename(columns={'CANTIDAD':'ASIGNADO'})
	legos_tsp.insert(len(legos_tsp.keys()),'ORDEN',0)
	
	verificados_tsp = verificados[['CODIGODESPACHO','CODIGOARTICULO','CANTIDAD','RESISTENCIA','RESISTENCIA_PASILLO','VOLUMEN','PESO','CONTAMINANTE','NAVE','PASILLO','RACK','X_PASILLO_LOCAL','COORDENADAYLOCAL']].copy()
	verificados_tsp.columns=['CODIGODESPACHO','CB','CANTIDAD','RESISTENCIA','RESISTENCIA_PASILLO','VOLUMEN','PESO','CONTAMINANTE','NAVE','PASILLO','RACK','X','Y']
	palletMetrics, pallets, legos = getMetrics(pallets_tsp,legos_tsp,codigodespacho,distances,parametros,verificados_tsp)
	
	return palletMetrics, pallets, legos

def direccionPicking(pallets_global_tsp, legos_global_tsp, distances, rutas, verificados, finesDePasillo):
	
	pallets = pallets_global_tsp.copy()
	legos = legos_global_tsp.copy()
	if len(pallets) > 0:
		pallets = pallets_global_tsp.merge(verificados[['CODIGODESPACHO','CODIGOARTICULO','PASILLO','X_PASILLO_LOCAL','COORDENADAYLOCAL']],left_on=['CODIGODESPACHO','CB'],right_on=['CODIGODESPACHO','CODIGOARTICULO'],how='left')
		pallets = pallets.sort_values(by=['PALLET_IDX','ORDEN'])
		pallets = pallets.reset_index(drop=True)
		index_pallets = pallets[['PALLET_IDX','PASILLO']].drop_duplicates().reset_index(drop=True)
	if len(legos) > 0:
		legos = legos_global_tsp.merge(verificados[['CODIGODESPACHO','CODIGOARTICULO','PASILLO','X_PASILLO_LOCAL','COORDENADAYLOCAL']],left_on=['CODIGODESPACHO','CB'],right_on=['CODIGODESPACHO','CODIGOARTICULO'],how='left')
		legos = legos.sort_values(by=['PALLET_IDX','LEGO_IDX','ORDEN'])
		legos = legos.reset_index(drop=True)
		index_legos =legos[['LEGO_IDX','PASILLO']].drop_duplicates().reset_index(drop=True)
	camino_pallet = pandas.DataFrame()
	camino_lego = pandas.DataFrame()
	pasillo_dir_pallet = pandas.DataFrame()
	pasillo_dir_lego = pandas.DataFrame()
	if len(pallets) > 0:
		for idx,row in index_pallets.iterrows():
			pallet_temp = pallets[(pallets.PALLET_IDX == row.PALLET_IDX)&(pallets.PASILLO == row.PASILLO)]
			inicio_temp = pallet_temp.head(1)
			inicio_temp.insert(len(inicio_temp.keys()),'POSICION','INICIO')
			fin_temp = pallet_temp.tail(1)
			fin_temp.insert(len(fin_temp.keys()),'POSICION','FIN')
			temp_pasillo = inicio_temp.append(fin_temp)
			temp_pasillo = temp_pasillo.reset_index(drop=True)
			camino_pallet = camino_pallet.append(temp_pasillo)
			if row.PASILLO == 98:
				pasillo_dir_pallet = pasillo_dir_pallet.append(pandas.DataFrame({'PALLET_IDX':[row.PALLET_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[1]}))
			elif row.PASILLO == 99:
				pasillo_dir_pallet = pasillo_dir_pallet.append(pandas.DataFrame({'PALLET_IDX':[row.PALLET_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[2]}))
			elif temp_pasillo.COORDENADAYLOCAL[0] < temp_pasillo.COORDENADAYLOCAL[1]:
				pasillo_dir_pallet = pasillo_dir_pallet.append(pandas.DataFrame({'PALLET_IDX':[row.PALLET_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[2]}))
			elif temp_pasillo.COORDENADAYLOCAL[0] > temp_pasillo.COORDENADAYLOCAL[1]:
				pasillo_dir_pallet = pasillo_dir_pallet.append(pandas.DataFrame({'PALLET_IDX':[row.PALLET_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[1]}))
		if len(pasillo_dir_pallet) > 0:
			pallets = pallets.merge(pasillo_dir_pallet, left_on = ['PALLET_IDX','PASILLO'], right_on = ['PALLET_IDX','PASILLO'], how = 'left')
		else:
			pallets.insert(len(pallets.keys()),'DIR_PASILLO',0)
		camino_pallet = camino_pallet.reset_index(drop=True)
		camino_pallet['UBICACION']='0'
		camino_pallet['PASILLO_ANT']=0
		for idx,row in camino_pallet.iterrows():
			if idx > 0 and row.POSICION == 'INICIO' and camino_pallet.loc[idx-1,'POSICION'] == 'FIN' and row.PALLET_IDX == camino_pallet.loc[idx-1,'PALLET_IDX']:
				cb_1 = 'cb_' + camino_pallet.loc[idx-1,'CODIGOARTICULO']
				cb_2 = 'cb_' + row.CODIGOARTICULO
				ruta_par = rutas[row.NAVE][cb_1][cb_2][1]
				posicion_fin = ruta_par[-1]
				camino_pallet.loc[idx,'UBICACION'] = posicion_fin
				camino_pallet.loc[idx,'PASILLO_ANT'] = camino_pallet.loc[idx-1,'PASILLO']
		camino_pallet = camino_pallet.merge(finesDePasillo[['NAVE','PASILLO','UBICACION','DIRECCION']], left_on =['NAVE','PASILLO_ANT','UBICACION'], right_on =['NAVE','PASILLO','UBICACION'], how = 'left')
		camino_pallet = camino_pallet.drop(columns={'PASILLO_y'})
		camino_pallet = camino_pallet.rename(columns={'PASILLO_x':'PASILLO'})
		camino_cambio = camino_pallet[camino_pallet.DIRECCION > 0]
		pallets = pallets.merge(camino_cambio[['PALLET_IDX','CB','PASILLO','DIRECCION']],left_on = ['PALLET_IDX','CB','PASILLO'], right_on = ['PALLET_IDX','CB','PASILLO'],how='left')
		pallets = pallets.fillna(0)
		pallets['VALORTIPODIRECCION'] = 0
		pallets.loc[(pallets.DIR_PASILLO>0)&(pallets.DIRECCION==0),'VALORTIPODIRECCION'] = pallets.DIR_PASILLO
		pallets.loc[(pallets.DIRECCION>0),'VALORTIPODIRECCION'] = pallets.DIRECCION
		en_cero = pallets[pallets.VALORTIPODIRECCION==0]
		for idx,row in en_cero.iterrows():
			if idx < len(pallets)-1:
				pallets.loc[idx,'VALORTIPODIRECCION'] = pallets.loc[idx+1,'VALORTIPODIRECCION']
			else:
				pallets.loc[idx,'VALORTIPODIRECCION'] = 1
		pallets = pallets.drop(columns = {'DIR_PASILLO','DIRECCION'})
	if len(legos) > 0:
		for idx,row in index_legos.iterrows():
			lego_temp = legos[(legos.LEGO_IDX == row.LEGO_IDX)&(legos.PASILLO == row.PASILLO)]
			inicio_temp = lego_temp.head(1)
			inicio_temp.insert(len(inicio_temp.keys()),'POSICION','INICIO')
			fin_temp = lego_temp.tail(1)
			fin_temp.insert(len(fin_temp.keys()),'POSICION','FIN')
			temp_pasillo = inicio_temp.append(fin_temp)
			temp_pasillo = temp_pasillo.reset_index(drop=True)
			camino_lego = camino_lego.append(temp_pasillo)
			if row.PASILLO == 98:
				pasillo_dir_lego = pasillo_dir_lego.append(pandas.DataFrame({'LEGO_IDX':[row.LEGO_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[1]}))
			elif row.PASILLO == 99:
				pasillo_dir_lego = pasillo_dir_lego.append(pandas.DataFrame({'LEGO_IDX':[row.LEGO_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[2]}))
			elif temp_pasillo.COORDENADAYLOCAL[0] < temp_pasillo.COORDENADAYLOCAL[1]:
				pasillo_dir_lego = pasillo_dir_lego.append(pandas.DataFrame({'LEGO_IDX':[row.LEGO_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[2]}))
			elif temp_pasillo.COORDENADAYLOCAL[0] > temp_pasillo.COORDENADAYLOCAL[1]:
				pasillo_dir_lego = pasillo_dir_lego.append(pandas.DataFrame({'LEGO_IDX':[row.LEGO_IDX],'PASILLO':[row.PASILLO],'DIR_PASILLO':[1]}))	
		if len(pasillo_dir_lego) > 0:
			legos = legos.merge(pasillo_dir_lego, left_on = ['LEGO_IDX','PASILLO'], right_on = ['LEGO_IDX','PASILLO'], how = 'left')
		else:
			legos.insert(len(legos.keys()),'DIR_PASILLO',0)
		camino_lego = camino_lego.reset_index(drop=True)
		camino_lego.insert(len(camino_lego.keys()),'UBICACION','0')
		camino_lego.insert(len(camino_lego.keys()),'PASILLO_ANT',0)
		for idx,row in camino_lego.iterrows():
			if idx > 0 and row.POSICION == 'INICIO' and camino_lego.loc[idx-1,'POSICION'] == 'FIN' and row.LEGO_IDX == camino_lego.loc[idx-1,'LEGO_IDX']:
				cb_1 = 'cb_' + camino_lego.loc[idx-1,'CODIGOARTICULO']
				cb_2 = 'cb_' + row.CODIGOARTICULO
				ruta_par = rutas[row.NAVE][cb_1][cb_2][1]
				posicion_fin = ruta_par[-1]
				camino_lego.loc[idx,'UBICACION'] = posicion_fin
				camino_lego.loc[idx,'PASILLO_ANT'] = camino_lego.loc[idx-1,'PASILLO']
		camino_lego = camino_lego.merge(finesDePasillo[['NAVE','PASILLO','UBICACION','DIRECCION']], left_on =['NAVE','PASILLO_ANT','UBICACION'], right_on =['NAVE','PASILLO','UBICACION'], how = 'left')
		camino_lego = camino_lego.drop(columns={'PASILLO_y'})
		camino_lego = camino_lego.rename(columns={'PASILLO_x':'PASILLO'})
		camino_cambio = camino_lego[camino_lego.DIRECCION > 0]
		legos = legos.merge(camino_cambio[['LEGO_IDX','CB','PASILLO','DIRECCION']],left_on = ['LEGO_IDX','CB','PASILLO'], right_on = ['LEGO_IDX','CB','PASILLO'],how='left')
		legos = legos.fillna(0)
		legos['VALORTIPODIRECCION'] = 0
		legos.loc[(legos.DIR_PASILLO>0)&(legos.DIRECCION==0),'VALORTIPODIRECCION'] = legos.DIR_PASILLO
		legos.loc[(legos.DIRECCION>0),'VALORTIPODIRECCION'] = legos.DIRECCION
		en_cero = legos[legos.VALORTIPODIRECCION==0]
		for idx,row in en_cero.iterrows():
			if idx < len(legos)-1:
				legos.loc[idx,'VALORTIPODIRECCION'] = legos.loc[idx+1,'VALORTIPODIRECCION']
			else:
				legos.loc[idx,'VALORTIPODIRECCION'] = 1
		legos = legos.drop(columns = {'DIR_PASILLO','DIRECCION'})	
	if len(pallets) > 0:
		pallets.loc[(pallets.VALORTIPODIRECCION==0),'VALORTIPODIRECCION'] = 2
		pallets = pallets[['CODIGODESPACHO','NAVE','PALLET_IDX','CB','ASIGNADO','ORDEN','VALORTIPODIRECCION','BASE']]
		pallets.at[:,'VALORTIPODIRECCION'] = pallets.VALORTIPODIRECCION.fillna(2)
	if len(legos) > 0:
		legos.loc[(legos.VALORTIPODIRECCION==0),'VALORTIPODIRECCION'] = 2
		legos = legos[['CODIGODESPACHO','NAVE','PALLET_IDX','LEGO_IDX','CB','ASIGNADO','ORDEN','VALORTIPODIRECCION','BASE']]
		legos.at[:,'VALORTIPODIRECCION'] = legos.VALORTIPODIRECCION.fillna(2)
	return pallets, legos

#Almacenamiento de resultados en archivos .pickle y .xlsx
def guardarResultados(verificados, pallets_global_tsp,legos_global_tsp,palletSiError,resumen_global,metrics_global,resumen_tareas, estado_despachos, codestr):
	
	if len(pallets_global_tsp) == 0 and len(pallets_global_tsp.keys())<7:
		pallets_global_tsp = pandas.DataFrame(columns = ['CODIGODESPACHO','NAVE','ID_PALLET','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','BASE'])
	if len(legos_global_tsp) == 0 and len(legos_global_tsp.keys())<8:
		legos_global_tsp = pandas.DataFrame(columns = ['CODIGODESPACHO','NAVE','ID_PALLET','ID_LEGO','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','BASE'])
	if len(palletSiError) > 0:
		if not 'ID_LEGO' in palletSiError:
			palletSiError.insert(3,'ID_LEGO',palletSiError.ID_PALLET)
		if not 'BASE' in palletSiError:
			palletSiError.insert(7,'BASE',1)
	pallets_archivo = pandas.DataFrame()
	util.writeFile(estado_despachos,'estado_despachos'+codestr+'.pickle')
	if len(pallets_global_tsp)>0:
		pallets_global_tsp.columns = ['CODIGODESPACHO','NAVE','ID_PALLET','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','BASE']
		#pallets_global_tsp.to_excel('pallets_picking.xlsx')
	
		pallets_archivo = pallets_global_tsp.copy()
		if not 'ID_LEGO' in pallets_archivo:
			pallets_archivo.insert(3,'ID_LEGO',pallets_global_tsp.ID_PALLET)
	
	if len(legos_global_tsp)>0:
		legos_global_tsp.columns = ['CODIGODESPACHO','NAVE','ID_PALLET','ID_LEGO','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','BASE']
		#legos_global_tsp.to_excel('legos_picking.xlsx')
		pallets_archivo = pallets_archivo.append(legos_global_tsp).reset_index(drop=True)
	if len(pallets_archivo)>0:
		pallets_archivo = pallets_archivo.merge(verificados[['CODIGODESPACHO','CODIGOARTICULO','CODIGOUBICACION','CODIGOUNIDADMANEJO']], left_on = ['CODIGODESPACHO','CODIGOARTICULO'], right_on = ['CODIGODESPACHO','CODIGOARTICULO'], how = 'left')	
		#pallets_archivo.insert(len(pallets_archivo.keys()),'CODIGOTIPODIRECCION',0)
		resumen_global = resumen_global.rename(columns={'ID_PALLET':'ID_LEGO'})
	
	if len(palletSiError) > 0:
		pallets_archivo = pallets_archivo.append(palletSiError)
	if not 'ESTAREASINERROR' in pallets_archivo:
		pallets_archivo.insert(len(pallets_archivo.keys()),'ESTAREASINERROR',1)
	#pallets_archivo.to_excel('tareas_generadas.xlsx')
	
	util.writeFile(pallets_archivo,'tareas_generadas'+codestr+'.pickle')
	
	#metrics
	if len(metrics_global) > 0: 
		pallets_info = metrics_global[['CODIGODESPACHO','PALLET_IDX','LEGO_IDX']].drop_duplicates(subset=['CODIGODESPACHO','PALLET_IDX','LEGO_IDX'])
		metric_names = metrics_global.metric.unique()
		for i in metric_names:
			info_nueva = metrics_global[metrics_global.metric==i]
			pallets_info = pallets_info.merge(info_nueva[['PALLET_IDX','LEGO_IDX','value']], left_on=['PALLET_IDX','LEGO_IDX'], right_on=['PALLET_IDX','LEGO_IDX'],how='left')
			pallets_info = pallets_info.rename(columns={'value':i})
		pallets_info = pallets_info.fillna(0)
		#pallets_info.to_excel('pallets_info.xlsx')
		util.writeFile(pallets_info,'pallets_info'+codestr+'.pickle')

#Creacion de pallets y tareas para un despacho
def resolverDespacho(contador, desp, infoLocal, resistencia, distances, rutas, finesDePasillo, oplRelajado, oplInt, oplPallet, oplAgrupar, oplAgruparNave, MAXVOLUME, MAXWEIGHT, MAXVOLUME_FUR, MAXWEIGHT_FUR, PALLETCOST, NUMPALLETS, parametros_util, parametros, tareas_global, pallets_global_tsp,legos_global_tsp,resumen_global,metrics_global):
	
	tareas_despacho = pandas.DataFrame()
	resumen_despacho = pandas.DataFrame()
	naves = infoLocal.NAVE.unique()
	for nave in naves:
		contenidoFinal = pandas.DataFrame()
		resumenFinal = pandas.DataFrame()
		infoNave = infoLocal[infoLocal.NAVE == nave]
		patterns, patternCost = crearInicial(infoNave, resistencia, MAXVOLUME, MAXWEIGHT, PALLETCOST)
		mejor = 0
		curr = numpy.Infinity
		iteracion = 0
		demandaFaltante = infoNave[['CODIGOARTICULO','CANTIDAD']].copy()
		#CAMBIAR CONDICION
		logging.info('Creación de tareas nave '+str(nave))
		while (mejor != curr and iteracion < 100):
			mejor = curr
			curr, duales = oplMasterRelajado(oplRelajado, infoNave, patterns, patternCost)
			numPallet = patternCost['ID_PALLET'].max()
			newPattern, newPatternCost = oplAuxliar(oplPallet, parametros, infoNave, duales, resistencia, numPallet)
			if len(newPatternCost) < PALLETCOST:
				patterns = patterns.append(newPattern)
				patternCost = patternCost.append(newPatternCost)
				#demandaFaltante, duales = definirDuales(demandaFaltante, duales, newPattern)
			iteracion += 1
		contenido, resumen = oplMasterINT(oplInt, infoNave, patterns, patternCost, nave)
		resumenPallets, pallets = eliminarExcesos(contenido,resumen,infoNave)
		completos, numPallets, subpallets, contents, infoPeso, infoVol, info_agrupar = definicionSubpallets(parametros, resistencia, infoNave, resumenPallets, pallets)
		
		resumenFinal = resumenPallets[['ID_PALLET','PESO','VOLUMEN']].copy()
		resumenFinal.insert(0,'ID_new',resumenFinal.ID_PALLET+contador)
		resumenFinal = resumenFinal.drop(columns=['ID_PALLET'])
		resumenFinal = resumenFinal.rename(columns={"ID_new": "ID_PALLET"})
		contenidoFinal = pallets.copy()
		contenidoFinal.insert(0,'ID_new',contenidoFinal.ID_PALLET+contador)
		contenidoFinal = contenidoFinal.drop(columns=['ID_PALLET'])
		contenidoFinal = contenidoFinal.rename(columns={"ID_new": "ID_PALLET"})
		
		if numPallets > 0:
			resumenParcial = resumenPallets[resumenPallets.ID_PALLET.isin(completos)]#[['ID_PALLET','PESO','VOLUMEN']]
			contenidoParcial = pallets[pallets.ID_PALLET.isin(completos)]
			indice = parametros[parametros.PARAMETER=='NUMPALLETS'].index[0]
			parametros.loc[indice,'VALUE'] = len(resumenPallets)
			tareasAgrupar, unionPallets = oplAgregar(oplAgrupar, parametros, info_agrupar, resistencia, subpallets, contents, infoPeso, infoVol)	
			if len(tareasAgrupar) > 0:
				contenidoAgrupar = pandas.DataFrame()
				
				recorrer = resumenParcial.copy()
				
				for idx,row in recorrer.iterrows():
					resumenParcial.at[idx,'ID_PALLET'] = contador
					contenido_pallet = contenidoParcial[contenidoParcial.ID_PALLET==row.ID_PALLET]
					contenido_pallet = contenido_pallet.drop(columns = ['ID_PALLET'])
					contenido_pallet.insert(0,'ID_PALLET',contador)
					contenidoAgrupar = contenidoAgrupar.append(contenido_pallet)
					contador += 1
				for idx,row in tareasAgrupar.iterrows():
					tareasAgrupar.at[idx,'ID_PALLET'] = contador
					sub = unionPallets[unionPallets.pallet==row.ID_PALLET]['subpallet']
					contenido_pallet = pallets[pallets.ID_PALLET.isin(sub)]
					contenido_pallet = contenido_pallet.drop(columns = ['ID_PALLET'])
					contenido_pallet.insert(0,'ID_PALLET',contador)
					contenidoAgrupar = contenidoAgrupar.append(contenido_pallet)
					contador += 1														
				resumenParcial = resumenParcial.append(tareasAgrupar)
				resumenFinal = resumenParcial
				contenidoFinal = contenidoAgrupar
		else:
			contador = resumenFinal.ID_PALLET.max() + 1

		resumenFinal.columns = ['ID_PALLET','PESO','VOLUMEN']
		contenidoFinal.columns= ['ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD']
		contenidoFinal = contenidoFinal.merge(infoNave[['CODIGOARTICULO','CODIGOUNIDADMANEJO','PASILLO','RACK']],left_on=['CODIGOARTICULO','CODIGOUNIDADMANEJO'], right_on = ['CODIGOARTICULO','CODIGOUNIDADMANEJO'], how= 'left')
		
		resumenFinal.insert(0,'NAVE',nave)
		resumenFinal.insert(0,'CODIGODESPACHO',desp)
		resumen_despacho = resumen_despacho.append(resumenFinal)
		contenidoFinal.insert(0,'NAVE',nave)
		contenidoFinal.insert(0,'CODIGODESPACHO',desp)
		tareas_despacho = tareas_despacho.append(contenidoFinal)	
	
	#Agrupar entre naves
	logging.info('Estibaje entre naves')
	tareas_despacho = tareas_despacho.groupby(['CODIGODESPACHO','NAVE','ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO','PASILLO','RACK'], as_index=False).CANTIDAD.sum()
	pallets_completos, numPallets, subpallets, content, infoPeso, infoVol, info_agrupar = definicionSubpalletNaves(parametros, resistencia, infoLocal, resumen_despacho, tareas_despacho)
	
	if numPallets > 0:
		pallet_agrupado, agrupacion = oplAgregarNaves(oplAgruparNave, parametros, infoLocal, resistencia, subpallets, content, infoPeso, infoVol)
	else: 
		pallet_agrupado = resumen_despacho[['ID_PALLET','PESO','VOLUMEN']]
		agrupacion = pandas.DataFrame({'pallet':pallets_completos,'subpallet':pallets_completos,'base':1})
	
	tareas_legos, tareas_pallets, resumen_tareas, resumen_pallets, contador = crearPalletLegos(pallet_agrupado, agrupacion, tareas_despacho, resumen_despacho, desp, contador)
	logging.info('Creación de rutas de picking')
	#pdb.set_trace()
	palletMetrics, pallets_tsp, legos_tsp = generarPicking(tareas_pallets,tareas_legos,desp,distances,parametros_util,infoLocal)
	palletMetrics.insert(0,'CODIGODESPACHO',desp)

	tareas_global = tareas_global.append(tareas_despacho)
	resumen_global = resumen_global.append(resumen_despacho)
	
	#Picking
	logging.info('Almacenamiento de tareas')
	pallets_global_tsp = pallets_global_tsp.append(pallets_tsp)
	legos_global_tsp = legos_global_tsp.append(legos_tsp)
	metrics_global = metrics_global.append(palletMetrics)
	
	#determinar direccion de recoleccion
	
	return contador,pallets_global_tsp,legos_global_tsp,resumen_global,metrics_global,resumen_tareas

#Metodo main: creacion de pallets y tareas para una lista de verificados
#Verificados -> pedido acumulado de todos los despachos con prueba de calidad de datos aplicada
def main(archivo,inicial,codestr):
	#Info verificados
	logging.info('-----' + codestr + '-----')
	print('Inicio de creacion de tareas optimizadas')
	logging.info('Inicio de creacion de tareas optimizadas')
	verificados = util.readFile(archivo)
	sol_inicial = util.readFile(inicial)
	verificados['CODIGOARTICULO'] = verificados.CODIGOARTICULO.astype(str)
	verificados['CONTAMINANTE'] = verificados.CONTAMINANTE.astype(str)
	verificados['CODIGOUNIDADMANEJO'] = verificados.CODIGOUNIDADMANEJO.astype(int)
	verificados['CANTIDAD'] = verificados.CANTIDAD.astype(int)
	verificados['NIVEL'] = verificados.NIVEL.astype(int)
	verificados['RACK'] = verificados.RACK.astype(int)
	#fines de pasillo
	finesDePasillo = util.readFile('finesDePasillo.xlsx',relPathToParam)
	#Info resistencias
	resistencia = util.readFile('resistencias.xlsx',relPathToParam)
	#Info parametros
	parametros_util = util.readFile('parametros.xlsx',relPathToParam)
	parametros_util = parametros_util.set_index('parameter')
	#Modelos OPL
	oplRelajado = os.path.join(relPathToOPL,'choosePalletsRelajado.mod')
	oplInt = os.path.join(relPathToOPL,'choosePalletsInt.mod')
	oplPallet = os.path.join(relPathToOPL,'createPallets.mod')
	oplAgrupar = os.path.join(relPathToOPL,'Agrupar.mod')
	oplAgruparNave = os.path.join(relPathToOPL,'AgruparNaves.mod')
	#distancias entre articulos
	distances = {}
	for nave in verificados.NAVE.unique():
		distances[nave] = util.readFile('distanciasAbastos_{}_{}.pickle'.format(nave, codestr))
	rutas = {}
	for nave in verificados.NAVE.unique():
		rutas[nave] = util.readFile('rutasAbastos_{}_{}.pickle'.format(nave, codestr))
	MAXVOLUME = parametros_util.loc['maxVolume','value']
	MAXWEIGHT = parametros_util.loc['maxWeight','value']
	MAXVOLUME_FUR = parametros_util.loc['targetLoadVolume','value']
	MAXWEIGHT_FUR = parametros_util.loc['targetLoadWeight','value']
	PALLETCOST = 10
	DISTANCECOST = parametros_util.loc['distancePenalty','value']
	NUMPALLETS = 20
	MAXLEGOS = parametros_util.loc['maxLegos','value']
	
	inicio = time.time()
	despachos = verificados.CODIGODESPACHO.unique()
	num_despachos = len(despachos)
	cont_despacho = 0
	tareas_global = pandas.DataFrame()
	pallets_global_tsp = pandas.DataFrame()
	legos_global_tsp = pandas.DataFrame()
	resumen_global = pandas.DataFrame()
	metrics_global = pandas.DataFrame()
	resumen_tareas = pandas.DataFrame()
	estado_despachos = pandas.DataFrame()
	palletSiError = pandas.DataFrame()
	contador = 0

	if len(despachos) == 0:
		logging.info('No hay despachos disponibles para optimizar')
		print('No hay despachos disponibles para optimizar')
	else:
		for desp in despachos:
			print(desp)
			logging.info('Inicio del despacho: '+str(desp))
			parametros = pandas.DataFrame({'PARAMETER':['MAXVOLUME','MAXWEIGHT','MAXVOLUME_FUR','MAXWEIGHT_FUR','PALLETCOST','DISTANCECOST','NUMPALLETS','MAXLEGOS'],'VALUE':[MAXVOLUME,MAXWEIGHT,MAXVOLUME_FUR,MAXWEIGHT_FUR,PALLETCOST,DISTANCECOST,NUMPALLETS,MAXLEGOS]})
			infoLocal = verificados[verificados.CODIGODESPACHO == desp]
			try:
				contador,pallets_global_tsp,legos_global_tsp,resumen_global,metrics_global,resumen_tareas = resolverDespacho(contador, desp, infoLocal, resistencia, distances, rutas, \
				finesDePasillo, oplRelajado, oplInt, oplPallet, oplAgrupar, oplAgruparNave, MAXVOLUME, MAXWEIGHT, MAXVOLUME_FUR, MAXWEIGHT_FUR, PALLETCOST, NUMPALLETS, parametros_util, \
				parametros, tareas_global, pallets_global_tsp,legos_global_tsp,resumen_global,metrics_global)
				df = pandas.DataFrame({'CODIGODESPACHO':[desp],'VALORESTADOPROCESO':['TER']})
				estado_despachos = estado_despachos.append(df,ignore_index=True)
				logging.info('Fin del despacho: '+str(desp))
			except Exception as e:
				#pdb.set_trace()
				errorMessage = "%s with exception %s" % (desp, e)
				logging.info(errorMessage)
				print(errorMessage)
				df = pandas.DataFrame({'CODIGODESPACHO':[desp],'VALORESTADOPROCESO':['ERR']})
				estado_despachos = estado_despachos.append(df,ignore_index=True)
				tareas_ini = pandas.DataFrame()
				#pdb.set_trace()
				if type(sol_inicial.CODIGODESPACHO[0])==str:
					tareas_ini = sol_inicial[sol_inicial.CODIGODESPACHO==desp]
				else:
					tareas_ini = sol_inicial[sol_inicial.CODIGODESPACHO==int(desp)]
				tareas_ini['ID_PALLET'] = tareas_ini.ID_PALLET + contador
				contador = tareas_ini.ID_PALLET.max()+1
				palletSiError = palletSiError.append(tareas_ini)
				logging.info('Fin del despacho CON ERROR: ' + str(desp))
			cont_despacho = cont_despacho + 1
			porcentaje = round((cont_despacho/num_despachos)*100,2)
			print('Completado: ' + str(porcentaje) +'%  ' + str(cont_despacho) + ' de '+ str(num_despachos) + ' despachos completados')
		pallets_global_tsp = pallets_global_tsp.reset_index(drop=True)
		legos_global_tsp = legos_global_tsp.reset_index(drop=True)
		pallets_global_tsp, legos_global_tsp = direccionPicking(pallets_global_tsp, legos_global_tsp, distances, rutas, verificados, finesDePasillo)
		pallets_global_tsp = pallets_global_tsp.drop_duplicates().reset_index(drop=True)
		legos_global_tsp = legos_global_tsp.drop_duplicates().reset_index(drop=True)
		guardarResultados(verificados,pallets_global_tsp,legos_global_tsp,palletSiError,resumen_global,metrics_global,resumen_tareas,estado_despachos,codestr)
		
		fin = time.time() - inicio
		print('Fin optimizacion - Tiempo de ejecucion: ' + str(fin))
		logging.info('Fin optimizacion - Tiempo de ejecucion: ' + str(fin))

if __name__ == "__main__":
	main('Verificados12990_1583902800000_PEA_10_3100.pickle','tareas_inicial_generadas12990_1583902800000_PEA_10_3100.pickle','12990_1583902800000_PEA_10_3100')

