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

if sys.platform.startswith('win'):
	sys.path.append(os.path.relpath("..\\utilities"))
else:
	sys.path.append(os.path.relpath("../utilities"))
	
import util
import hamiltonian

relPathToParam = "..\\Parametros\\"
if not sys.platform.startswith('win'):
	relPathToParam = "../Parametros/"
 
def creacionTareas(infoNave, Resistance, MAXVOLUME, MAXPESO, PALLETCOST, pattern):
	#pdb.set_trace()
	Resistance = Resistance.set_index('RESISTENCIA')
	index_resist = Resistance.index
	patterns = pandas.DataFrame(columns=['ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','ORDEN'])
	patternInfo = pandas.DataFrame(columns=['ID_PALLET','PESO','VOLUMEN'])
	#pattern = 0	

	infoNave.insert(len(infoNave.keys()),'checked','False')
	infoNaveCopy = infoNave.copy()
	
	for idx, row in infoNave.iterrows():
		#print(row[1])
		maxUnits = int(min(MAXPESO/row.PESO,Resistance.loc[row.RESISTENCIA,'maxPeso'] / row.PESO, MAXVOLUME / row.VOLUMEN, row.CANTIDAD))
		if maxUnits == int(Resistance.loc[row.RESISTENCIA,'maxPeso'] / row.PESO) or maxUnits == int(MAXVOLUME / row.VOLUMEN) or maxUnits == int(MAXPESO / row.PESO):
			#pdb.set_trace()
			cantidad = math.ceil(row.CANTIDAD/maxUnits)
			
			for i in range(pattern,cantidad+pattern):
				pat = pandas.DataFrame({'ID_PALLET':[pattern],'CODIGOARTICULO':[row.CODIGOARTICULO],'CODIGOUNIDADMANEJO':[row.CODIGOUNIDADMANEJO],'CANTIDAD':[maxUnits]})
				pat.insert(4,'ORDEN',numpy.arange(len(pat)))
				patterns = patterns.append(pat)
				patternInfo = patternInfo.append(pandas.DataFrame({'ID_PALLET':[pattern],'PESO':[maxUnits*row.PESO],'VOLUMEN':[maxUnits*row.VOLUMEN]}))
				pattern += 1
				#pdb.set_trace()
			#pdb.set_trace()
			infoNaveCopy.loc[idx,'checked'] = 'True'
	
	contaminables = infoNaveCopy[infoNaveCopy.CONTAMINANTE == 'CONTAMINABLE']
	contaminantes = infoNaveCopy[infoNaveCopy.CONTAMINANTE != 'CONTAMINABLE']
	#pdb.set_trace()
	#Agrupar contaminables
	pasillosNoCont = contaminables.sort_values(by=['PASILLO','RACK']) #RACK?
	while pasillosNoCont[pasillosNoCont.checked=='False']['checked'].count()>0:
		pesoResistencia = pandas.DataFrame({'resistencia':index_resist,'peso':0})
		peso = 0
		volumen = 0
		nuevo_pattern = pandas.DataFrame()
		recorrer = pasillosNoCont[pasillosNoCont.checked=='False']
		for idx, row in recorrer.iterrows():
			#print(row)
			if row.checked == 'False' and peso < MAXPESO and volumen < MAXVOLUME:
				pesoR = pesoResistencia.loc[row.RESISTENCIA,'peso'] + row.CANTIDAD * row.PESO
				pesoT = peso + row.CANTIDAD * row.PESO
				vol = volumen + row.CANTIDAD * row.VOLUMEN
				#pdb.set_trace()
				if pesoT < MAXPESO and vol < MAXVOLUME and pesoR <= Resistance.loc[row.RESISTENCIA,'maxPeso']:
					#pdb.set_trace()
					pesoResistencia.loc[row.RESISTENCIA,'peso'] = pesoR
					peso = pesoT
					volumen = vol
					pasillosNoCont.loc[idx,'checked'] = 'True'
					nuevo = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'CODIGOARTICULO':[row.CODIGOARTICULO],'CODIGOUNIDADMANEJO':[row.CODIGOUNIDADMANEJO],'CANTIDAD':[row .CANTIDAD]})
					nuevo_pattern = nuevo_pattern.append(nuevo)		
		
		nuevoCosto = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'PESO':[peso],'VOLUMEN':[volumen]})
		#determinar orden
		#print(len(nuevo_pattern))
		if len(nuevo_pattern) > 0:
			nuevo_pattern.insert(4,'ORDEN',numpy.arange(len(nuevo_pattern)))
			patterns = patterns.append(nuevo_pattern)
			patternInfo = patternInfo.append(nuevoCosto)
		pattern = pattern + 1
	#pdb.set_trace()
	#agrupar contaminantes
	pasillosCont = contaminantes.sort_values(by=['PASILLO','RACK'])
	while pasillosCont[pasillosCont.checked=='False']['checked'].count()>0:
		pesoResistencia = pandas.DataFrame({'resistencia':index_resist,'peso':0})
		peso = 0
		volumen = 0
		nuevo_pattern = pandas.DataFrame()
		recorrer = pasillosCont[pasillosCont.checked=='False']
		for idx, row in pasillosCont.iterrows():
			#print(row)
			if row.checked == 'False' and peso < MAXPESO and volumen < MAXVOLUME:
				pesoR = pesoResistencia.loc[row.RESISTENCIA,'peso'] + row.CANTIDAD * row.PESO
				pesoT = peso + row.CANTIDAD * row.PESO
				vol = volumen + row.CANTIDAD * row.VOLUMEN
				#pdb.set_trace()
				if pesoT < MAXPESO and vol < MAXVOLUME and pesoR <= Resistance.loc[row.RESISTENCIA,'maxPeso']:
					#pdb.set_trace()
					pesoResistencia.loc[row.RESISTENCIA,'peso'] = pesoR
					peso = pesoT
					volumen = vol
					pasillosCont.loc[idx,'checked'] = 'True'
					nuevo = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'CODIGOARTICULO':[row.CODIGOARTICULO],'CODIGOUNIDADMANEJO':[row.CODIGOUNIDADMANEJO],'CANTIDAD':[row .CANTIDAD]})
					nuevo_pattern = nuevo_pattern.append(nuevo)			
		
		nuevoCosto = pandas.DataFrame.from_dict({'ID_PALLET':[pattern],'PESO':[peso],'VOLUMEN':[volumen]})
		if len(nuevo_pattern) >0:
			nuevo_pattern.insert(4,'ORDEN',numpy.arange(len(nuevo_pattern)))
			patterns = patterns.append(nuevo_pattern)
			patternInfo = patternInfo.append(nuevoCosto)
		pattern = pattern + 1
	
	patterns = patterns.reset_index(drop=True)
	patternInfo = patternInfo.sort_values(['PESO','VOLUMEN']).set_index('ID_PALLET')
	empacado = patterns.groupby(['CODIGOARTICULO'], as_index=False).CANTIDAD.sum().sort_values('CANTIDAD').reset_index(drop=True).set_index('CODIGOARTICULO')
	#pdb.set_trace()
	for idx,row in infoNave.iterrows():
		#pdb.set_trace()
		barcode = row.CODIGOARTICULO
		demanda = row.CANTIDAD
		dif = empacado.loc[barcode,'CANTIDAD'] - demanda
		if dif > 0:
			#pdb.set_trace()
			tempPallet = patterns[patterns.CODIGOARTICULO == barcode][['ID_PALLET','CANTIDAD']].sort_values('CANTIDAD')
			for idx1,row1 in tempPallet.iterrows():
				#pdb.set_trace()
				if dif < row1.CANTIDAD:
					patterns.loc[idx1,'CANTIDAD'] = patterns.loc[idx1,'CANTIDAD'] - dif
					patternInfo.loc[row1.ID_PALLET,'PESO'] = patternInfo.loc[row1.ID_PALLET,'PESO'] - dif * row.PESO
					patternInfo.loc[row1.ID_PALLET,'VOLUMEN'] = patternInfo.loc[row1.ID_PALLET,'VOLUMEN'] - dif * row.VOLUMEN
					dif = 0
				elif dif >= row1.CANTIDAD:
					#pdb.set_trace()
					dif = dif - patterns.loc[idx1,'CANTIDAD']
					patternInfo.loc[row1.ID_PALLET,'PESO'] = patternInfo.loc[row1.ID_PALLET,'PESO'] - patterns.loc[idx1,'CANTIDAD'] * row.PESO
					patternInfo.loc[row1.ID_PALLET,'VOLUMEN'] = patternInfo.loc[row1.ID_PALLET,'VOLUMEN'] - patterns.loc[idx1,'CANTIDAD'] * row.VOLUMEN
					patterns.loc[idx1,'CANTIDAD'] = 0
	
	return patterns, patternInfo, pattern
	
def main(archivo):
	print('solucion inicial tareas')
	randnum =archivo.split('.')[0].replace('Verificados','')
	
	verificados, resistencia, parametros_util, direccion_ini = lecturaArchivos(archivo)
	
	MAXVOLUME = parametros_util.loc['maxVolume','value']
	MAXWEIGHT = parametros_util.loc['maxWeight','value']
	PALLETCOST = 10
	DISTANCECOST = 0.01
	
	despachos = verificados.CODIGODESPACHO.unique()
	num_despachos = len(despachos)
	cont_despacho = 0
	
	inicio = time.time()
	tareas_global = pandas.DataFrame()
	resumen_global = pandas.DataFrame()
	contador = 0
	for desp in despachos:
		print(desp)
		tareas_despacho = pandas.DataFrame()
		resumen_despacho = pandas.DataFrame()
		infoLocal = verificados[verificados.CODIGODESPACHO == desp]
		naves = infoLocal.NAVE.unique()
		#nave_actual = [5]
		#naves = numpy.array(list(filter(lambda x: x in nave_actual, naves)))
		for nave in naves:
			contenidoFinal = pandas.DataFrame()
			resumenFinal = pandas.DataFrame()
			infoNave = infoLocal[infoLocal.NAVE == nave]
			patterns, patternInfo, contador = creacionTareas(infoNave, resistencia, MAXVOLUME, MAXWEIGHT, PALLETCOST,contador)
			patterns.insert(0,'NAVE',nave)
			patternInfo.insert(0,'NAVE',nave)
			tareas_despacho = tareas_despacho.append(patterns)
			resumen_despacho = resumen_despacho.append(patternInfo)
		tareas_despacho.insert(0,'CODIGODESPACHO',desp)
		resumen_despacho.insert(0,'CODIGODESPACHO',desp)
		tareas_global = tareas_global.append(tareas_despacho)
		resumen_global = resumen_global.append(resumen_despacho)

	tareas_generadas = formatoTarea(verificados, tareas_global, direccion_ini)
	guardarSolucion(tareas_generadas,resumen_global,randnum)
	print('Fin solucion inicial - Tiempo de ejecucion: ' + str(time.time() - inicio))
	
def inicialDespacho(archivo, despacho, contador):
	verificados, resistencia, parametros_util, direccion_ini = lecturaArchivos(archivo)
	infoLocal = verificados[verificados.CODIGODESPACHO == despacho]
	MAXVOLUME = parametros_util.loc['maxVolume','value']
	MAXWEIGHT = parametros_util.loc['maxWeight','value']
	PALLETCOST = 10
	DISTANCECOST = 0.01
	tareas_despacho = pandas.DataFrame()
	resumen_despacho = pandas.DataFrame()
	naves = infoLocal.NAVE.unique()
	for nave in naves:
		contenidoFinal = pandas.DataFrame()
		resumenFinal = pandas.DataFrame()
		infoNave = infoLocal[infoLocal.NAVE == nave]
		patterns, patternInfo,contador = creacionTareas(infoNave, resistencia, MAXVOLUME, MAXWEIGHT, PALLETCOST,contador)
		patterns.insert(0,'NAVE',nave)
		patternInfo.insert(0,'NAVE',nave)
		tareas_despacho = tareas_despacho.append(patterns)
		resumen_despacho = resumen_despacho.append(patternInfo)
	
	tareas_despacho.insert(0,'CODIGODESPACHO',despacho)
	resumen_despacho.insert(0,'CODIGODESPACHO',despacho)
	
	tareas_generadas = formatoTarea(verificados, tareas_despacho, direccion_ini)
	
	return tareas_generadas, resumen_despacho
	
def lecturaArchivos(archivo):
	verificados = util.readFile(archivo)
	verificados['CODIGOARTICULO'] = verificados.CODIGOARTICULO.astype(str)
	verificados['CONTAMINANTE'] = verificados.CONTAMINANTE.astype(str)
	resistencia = util.readFile('resistencias.xlsx',relPathToParam)
	parametros_util = util.readFile('parametros.xlsx',relPathToParam)
	parametros_util = parametros_util.set_index('parameter')
	direccion_ini = util.readFile('direccionPasillos.xlsx',relPathToParam)
	
	return verificados, resistencia, parametros_util, direccion_ini

def ordenRecoleccion():
	return 0

def formatoTarea(verificados,tareas,direccion_ini):
	#formato pattern ['CODIGODESPACHO','NAVE','ID_PALLET','CODIGOARTICULO','CODIGOUNIDADMANEJO','CANTIDAD','ORDEN']
	tareas = tareas.merge(verificados[['CODIGODESPACHO','CODIGOARTICULO','CODIGOUNIDADMANEJO','CODIGOUBICACION','PASILLO']],left_on=['CODIGODESPACHO','CODIGOARTICULO','CODIGOUNIDADMANEJO'],right_on=['CODIGODESPACHO','CODIGOARTICULO','CODIGOUNIDADMANEJO'],how='left')
	tareas = tareas[['CODIGODESPACHO','NAVE','ID_PALLET','CODIGOARTICULO','CANTIDAD','ORDEN','CODIGOUBICACION','CODIGOUNIDADMANEJO','PASILLO']]
	tareas = tareas.merge(direccion_ini,left_on=['NAVE','PASILLO'],right_on=['NAVE','PASILLO'],how='left')
	recorrer = tareas.copy()
	for idx,row in recorrer.iterrows():
		if idx > 0 and tareas.loc[idx-1,'ID_PALLET'] == tareas.loc[idx,'ID_PALLET'] and tareas.loc[idx-1,'PASILLO'] != tareas.loc[idx,'PASILLO']:
			tareas.loc[idx,'VALORTIPODIRECCION'] = tareas.loc[idx-1,'VALORTIPODIRECCION']
	tareas = tareas.drop(columns={'PASILLO'})
	tareas.insert(len(tareas.keys()),'BASE',1)
	tareas.at[:,'VALORTIPODIRECCION']=tareas.VALORTIPODIRECCION.fillna(2)
	return tareas

def guardarSolucion(tareas,resumen,randnum):
	util.writeFile(tareas,'tareas_inicial_generadas'+randnum+'.pickle')
	util.writeFile(resumen,'resumen_inicial'+randnum+'.pickle')

if __name__ == "__main__":
	
	main('Verificados134_1581483600000_PEA_10_3100.pickle')
	
	