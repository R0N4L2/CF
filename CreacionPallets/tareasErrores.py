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


def main(archivo,contador):
	codestr = archivo.split(".")[0].replace('Error_Verificados','')
	print('Inicio generacion tareas con errores')
	inicio = time.time()
	verificados_error = util.readFile(archivo)
	despachos = verificados_error.CODIGODESPACHO.unique()
	
	tareas_error = pandas.DataFrame()
#	estado_desapachos_error = pandas.DataFrame()
	#contador = 0
	for desp in despachos:
		print(desp)
		error_despacho = verificados_error[verificados_error.CODIGODESPACHO==desp]
		sin_ubicacion = error_despacho[error_despacho.X_PASILLO_LOCAL.isnull()][['CODIGODESPACHO','NAVE','CODIGOARTICULO','CANTIDAD','CODIGOUBICACION','CODIGOUNIDADMANEJO','CONTAMINANTE']]
		
		if len(sin_ubicacion) > 0:
			sin_ubi_contaminante = sin_ubicacion[sin_ubicacion.CONTAMINANTE=='CONTAMINANTE']
			sin_ubi_contaminable = sin_ubicacion[sin_ubicacion.CONTAMINANTE!='CONTAMINANTE']
			if len(sin_ubi_contaminante) > 0:
				sin_ubi_contaminante.insert(2,'ID_PALLET',contador)
				sin_ubi_contaminante.insert(3,'ID_LEGO',contador)
				sin_ubi_contaminante.insert(6,'ORDEN',numpy.arange(len(sin_ubi_contaminante)))
				sin_ubi_contaminante.insert(len(sin_ubicacion.keys()),'VALORTIPODIRECCION',1)
				sin_ubi_contaminante.insert(len(sin_ubicacion.keys()),'BASE',1)
				tareas_error = tareas_error.append(sin_ubi_contaminante)
				#tareas_error = tareas_error.sort_values(by=['CODIGOUBICACION'])
				contador += 1
			if len(sin_ubi_contaminable) > 0:
				sin_ubi_contaminable.insert(2,'ID_PALLET',contador)
				sin_ubi_contaminable.insert(3,'ID_LEGO',contador)
				sin_ubi_contaminable.insert(6,'ORDEN',numpy.arange(len(sin_ubi_contaminable)))
				sin_ubi_contaminable.insert(len(sin_ubicacion.keys()),'VALORTIPODIRECCION',1)
				sin_ubi_contaminable.insert(len(sin_ubicacion.keys()),'BASE',1)
				tareas_error = tareas_error.append(sin_ubi_contaminable)
				#tareas_error = tareas_error.sort_values(by=['CODIGOUBICACION'])
				contador += 1
		
		con_ubicacion = error_despacho[~error_despacho.X_PASILLO_LOCAL.isnull()]
		naves = con_ubicacion.NAVE.unique()
		for nave in naves:
			con_ubicacion_nave = con_ubicacion[con_ubicacion.NAVE==nave]
			#pasillos = con_ubicacion_nave.PASILLO.unique()
			#for pas in pasillos:
			#error_pasillo = con_ubicacion_nave[con_ubicacion_nave.PASILLO==pas]
			error_pasillo = con_ubicacion_nave.sort_values(by = ['PASILLO','RACK'])
			info_tarea = error_pasillo[['CODIGODESPACHO','NAVE','CODIGOARTICULO','CANTIDAD','CODIGOUBICACION','CODIGOUNIDADMANEJO']]
			info_tarea.insert(2,'ID_PALLET',contador)
			info_tarea.insert(3,'ID_LEGO',contador)
			info_tarea.insert(6,'ORDEN',numpy.arange(len(info_tarea)))
			info_tarea.insert(len(info_tarea.keys()),'VALORTIPODIRECCION',1)
			info_tarea.insert(len(info_tarea.keys()),'BASE',1)
			tareas_error = tareas_error.append(info_tarea)
			contador += 1
#		estado_despachos_error = estado_desapachos_error.append(pandas.DataFrame({'CODIGODESPACHO':[desp],'VALORESTADOPROCESO':['TER']}))
	estado_despachos_error =pandas.DataFrame({'CODIGODESPACHO':despachos,'VALORESTADOPROCESO':['TER']*len(despachos)})
	tareas_error.insert(len(tareas_error.keys()),'ESTAREASINERROR',0)
	util.writeFile(tareas_error,'tareas_error'+codestr+'.pickle')
	util.writeFile(estado_despachos_error,'estado_desapachos_error'+codestr+'.pickle')
	fin = time.time() - inicio
	print('Fin tareas con errores - Tiempo de ejecucion : ' + str(fin))
	
if __name__ == "__main__":
	main('Error_Verificados94_1580446800000_PEA_20906_3100.pickle',0)
