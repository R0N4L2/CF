from datetime import datetime
today = datetime.now()
today = today.strftime("%d_%m_%Y")
import logging
logging.basicConfig(format='%(asctime)s: %(message)s',filename='log_MasterRun_'+today+'.log',filemode='a',level=logging.INFO,datefmt='%Y-%m-%d %H:%M:%S')

import importlib
from doopl.factory import *
import numpy
import pandas
import os
import sys
import pickle
import pdb
import time
if sys.platform.startswith('win'):
	sys.path.append(os.path.relpath("..\\CreacionPallets"))
else:
	sys.path.append(os.path.relpath("../CreacionPallets"))
import creacionTareas
import solucionInicial
import tareasErrores
if sys.platform.startswith('win'):
	sys.path.append(os.path.relpath("..\\utilities"))
else:
	sys.path.append(os.path.relpath("../utilities"))	
import util
import hamiltonian
import argparse
def arguments():

	codigoprocesotarea = None
	fechadespacho = None
	tipoobjetivodespacho = None
	bodega = None
	subbodega = None
	codigodespacho = None
	codestr="_".join(pandas.Series(sys.argv[1:]).str.replace(",","_").tolist())
	if len(sys.argv) == 3:
		codigoprocesotarea =int(sys.argv[1])
		codigodespacho = sys.argv[2].split(",")
	elif len(sys.argv)>=6:
		codigoprocesotarea =int(sys.argv[1])
		fechadespacho = int(sys.argv[2])
		tipoobjetivodespacho = sys.argv[3].split(",")
		bodega = sys.argv[4].split(",")
		subbodega = sys.argv[5].split(",")
		if len(sys.argv)==7:
			codigodespacho = sys.argv[6].split(",")
	return codigoprocesotarea, fechadespacho, tipoobjetivodespacho,bodega,subbodega,codigodespacho,codestr

if __name__ == "__main__":
	codigoprocesotarea, fechadespacho, tipoobjetivodespacho,bodega,subbodega,codigodespacho,codestr= arguments()
	logging.info('---------------Inicio de ejecucion: '+codestr+'---------------')
	print("codigoprocesotarea:");print(codigoprocesotarea)
	logging.info("codigoprocesotarea: " + str(codigoprocesotarea))
	print("\nfechadespacho:");print(fechadespacho)
	logging.info("fechadespacho: "+str(fechadespacho))
	print("\ntipoobjetivodespacho:");print(tipoobjetivodespacho)
	logging.info("tipoobjetivodespacho: "+str(tipoobjetivodespacho))
	print("\nbodega: ");print(bodega)
	logging.info("bodega: "+str(bodega))
	print("\nsubbodega: ");print(subbodega)
	logging.info("subbodega: "+str(subbodega))
	print("\ncodigodespacho:");print(codigodespacho)
	logging.info("codigodespacho: "+str(codigodespacho))
	verificados1 = 'Verificados'+codestr+'.pickle'
	#verificados= 'Verificados'+codestr+'.xlsx'
	errverificados="Error_Verificados"+codestr+".pickle"
	estadoDespacho="estado_despachos"+codestr+".pickle"
	estadoDespachoError='estado_desapachos_error'+codestr+'.pickle'
	tareaGenerada='tareas_generadas'+codestr+'.pickle'
	tareaErroresGeneradas='tareas_error'+codestr+'.pickle'
	infoTareas = 'pallets_info'+codestr+'.pickle'
	folder1= "../Datos/Historicos/"
	inicio = time.time()
	logging.info('Inicio verificacion de calidad de datos')
	#Inicio proceso de creacion de tareas
	inicio_ver = time.time()
	util.CheckProceso("VCD","",int(codigoprocesotarea))
	util.verificados(fechadespacho,codigoprocesotarea,bodega,subbodega,codigodespacho,tipoobjetivodespacho,codestr)
	df=util.readFile(verificados1)
	fin_ver = time.time() - inicio_ver
	logging.info('Fin verificacion de calidad de datos - tiempo: '+str(fin_ver))
	if type(df).__name__!="NoneType":
		logging.info('Inicio preparacion de corrida cplex')
		inicio_pre = time.time()
		df["VALORESTADOPROCESO"]="PRO"
		verdf=df.shape[0]>0
		df1=util.readFile(errverificados)
		if type(df1).__name__!="NoneType":
			df1["VALORESTADOPROCESO"]="PRO"
			df=pandas.concat([df[["CODIGODESPACHO","VALORESTADOPROCESO"]],df1[["CODIGODESPACHO","VALORESTADOPROCESO"]]])
		else:
			df=df[["CODIGODESPACHO","VALORESTADOPROCESO"]]
		df.CODIGODESPACHO=df.CODIGODESPACHO.astype(int)
		df=df.drop_duplicates().reset_index(drop=True)
		util.InsertUpdateManyTareaDespachosFile(df,int(codigoprocesotarea))
#		pdb.set_trace()
		util.articuloConError(errverificados,int(codigoprocesotarea))
		finesPasillo = 'finesDePasillo.xlsx'
		coordsBaseName = 'Abastos'
		logging.info('Inicio verificacion de ejecucion de modelo cplex')
		util.CheckProceso((1-verdf)*"X"+verdf*"E"+"MC","",int(codigoprocesotarea))
		fin_pre = time.time() - inicio_pre
		#pdb.set_trace()
		logging.info('Fin preparacion de corrida cplex - tiempo: '+str(fin_pre))
		if verdf:
			try:
				logging.info('Inicio creacion de matriz de distancias')
				inicio_ham = time.time()
				hamiltonian.createDistanceFile(verificados1, finesPasillo, coordsBaseName, codestr)
				fin_ham = time.time()-inicio_ham
				logging.info('Fin creacion de matriz de distancias - tiempo: '+str(fin_ham))
				logging.info('Inicio creacion de solucion inicial')
				inicio_ini = time.time()
				solucionInicial.main(verificados1)
				fin_ini = time.time() - inicio_ini
				logging.info('Fin creacion de solucion inicial - tiempo: '+str(fin_ini))
				sol_inicial = 'tareas_inicial_generadas'+codestr+'.pickle'
#Try run creacionTarea, if cannot build it, use the initial solution
				try:
					logging.info('Inicio creacion de tareas cplex')
					creacionTareas.main(verificados1,sol_inicial,codestr)
					logging.info('Fin creacion de tareas cplex')
					dfTareas = util.readFile(tareaGenerada)
					error1=""
				except Exception as e1:
					logging.warning('Error en la creacion de tareas cplex: '+e1)
					tareaGenerada=sol_inicial
					error1=e1
					dfTareas =None
					logging.warning('Actualizacion de estado de error en base de datos')
					util.CheckProceso("RDT",str(error1)[:1000],int(codigoprocesotarea))
				logging.info('Inicio escritura de estados de ejecucion a la base de datos')
				inicio_estado = time.time()
				util.InsertUpdateManyTareaDespachosFile(estadoDespacho,int(codigoprocesotarea))#** estado despacho dentro o fuera de cplex?
				fin_estado = time.time() - inicio_estado
				logging.info('FIn escritura de estados de ejecucion a la base de datos - tiempo: '+str(fin_estado))
				error2=""
#proceso insercion tareas
			except Exception as e:
				logging.warning('Error en la creacion de matriz de distancias o en la escritura de estados de ejecucion: '+e)
				error1=""
				error2=e
				dfTareas =None
		else:
			logging.warning('No existe un archivo de datos verificados')
			dfTareas,error1,error2 =None,"",""
#
		inicial_errores = 0
		if util.Length(dfTareas) > 0:
			inicial_errores = dfTareas.ID_PALLET.max() + 1
		if util.checkFile(errverificados):
			logging.info('Inicio creacion de tareas con error')
			inicio_error = time.time()
			tareasErrores.main(errverificados,inicial_errores)
			fin_error = time.time() - inicio_error
			logging.info('Fin creacion de tareas con error - tiempo: '+str(fin_error))
		dfErrores = util.readFile(tareaErroresGeneradas)
		if util.Length(dfTareas) > 0 and util.Length(dfErrores) > 0:
			logging.info('Concatenar tareas cplex con tareas con error')
			tareas_acumuladas = pandas.concat([dfTareas,dfErrores],ignore_index=True,sort=False)[['CODIGODESPACHO','NAVE','ID_PALLET','ID_LEGO','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','CODIGOUBICACION','CODIGOUNIDADMANEJO','BASE','ESTAREASINERROR']]
		elif util.Length(dfTareas) == 0 and util.Length(dfErrores)> 0:
			logging.info('Actualizar tareas con error como unicas tareas generadas - (No hay tareas cplex)')
			tareas_acumuladas = dfErrores[['CODIGODESPACHO','NAVE','ID_PALLET','ID_LEGO','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','CODIGOUBICACION','CODIGOUNIDADMANEJO','BASE','ESTAREASINERROR']]
		else:
			logging.info('Actualizar tareas cplex como unicas tareas generadas - (No hay tareas con error)')
			tareas_acumuladas = dfTareas[['CODIGODESPACHO','NAVE','ID_PALLET','ID_LEGO','CODIGOARTICULO','CANTIDAD','ORDEN','VALORTIPODIRECCION','CODIGOUBICACION','CODIGOUNIDADMANEJO','BASE','ESTAREASINERROR']]
		logging.info('Actualizar tipo de datos del archivo de salida')
		tareas_acumuladas[['CODIGODESPACHO','ID_PALLET','ID_LEGO','CODIGOARTICULO','ORDEN','VALORTIPODIRECCION','CODIGOUBICACION','CODIGOUNIDADMANEJO','BASE','ESTAREASINERROR']]=tareas_acumuladas[['CODIGODESPACHO','ID_PALLET','ID_LEGO','CODIGOARTICULO','ORDEN','VALORTIPODIRECCION','CODIGOUBICACION','CODIGOUNIDADMANEJO','BASE','ESTAREASINERROR']].astype(int)
		logging.info('Guardar archivo pickle con las tareas generadas')
		util.writeFile(tareas_acumuladas,tareaGenerada)
		logging.info('Inicio escritura de tareas a la base de datos')
		inicio_tareas = time.time()
		util.InsertTareas(tareas_acumuladas,int(codigoprocesotarea))
		fin_tareas = time.time() - inicio_tareas
		logging.info('Fin escritura de tareas a la base de datos - tiempo: '+str(fin_tareas))

		dfEstadoDespacho=util.readFile(estadoDespacho)
		dfEstadoDespachoError=util.readFile(estadoDespachoError)
		if util.Length(dfEstadoDespacho) > 0 and util.Length(dfEstadoDespachoError) > 0:
			dfEstadoDespacho= pandas.concat([dfEstadoDespacho,dfEstadoDespachoError.loc[~dfEstadoDespachoError.CODIGODESPACHO.isin(dfEstadoDespacho.CODIGODESPACHO)]],ignore_index=True,sort=False)
		elif util.Length(dfEstadoDespacho)==0 and util.Length(dfEstadoDespachoError) > 0:
			dfEstadoDespacho=dfEstadoDespachoError
		logging.info('Actualizacion de estados de ejecucion de despachos')
		inicio_estado = time.time()
		util.InsertUpdateManyTareaDespachosFile(dfEstadoDespacho,int(codigoprocesotarea))
		fin_estado = time.time() - inicio_estado
		logging.info('Fin actualizacion de estados de ejecucion de despachos - tiempo: '+str(fin_estado))
		logging.info('Traslado de archivos de tareas a carpeta de historicos')
		util.saveHistoricos(tareaGenerada)
		if util.checkFile(tareaErroresGeneradas):
			util.saveHistoricos(tareaErroresGeneradas)
		util.saveHistoricos(infoTareas)
		util.saveHistoricos(estadoDespacho)
#
		if error1=="":
			logging.info('Actualizacion de estado de escritua de tareas')
			util.CheckProceso("RDT",str(error2)[:1000],int(codigoprocesotarea))
		logging.info('Actualizacion de estado de finalizacion del proceso')
		util.CheckProceso("FPR","",int(codigoprocesotarea))
	else:
		logging.warning('Actualizacion de estado de verificacion de data: no hay data para: '+codestr)
		util.CheckProceso("VCD","No tiene data para:"+("codigoprocesotarea="+str(int(codigoprocesotarea))+",")*(codigoprocesotarea!=None)+("fechadespacho="+str(int(fechadespacho))+",")*(fechadespacho!=None)+\
    ("tipoobjetivodespacho="+str(int(tipoobjetivodespacho))+",")*(tipoobjetivodespacho!=None)+("bodega="+str(int(bodega))+",")*(bodega!=None)+("subbodega="+str(int(subbodega))+",")*(subbodega!=None)+\
    ("codigodespacho="+str(int(codigodespacho))+",")*(codigodespacho!=None),int(codigoprocesotarea))
	#util.saveHistoricos(verificados)
	logging.info('Traslado de archivos de datos a carpeta de historicos')
	util.saveHistoricos(verificados1)
	util.saveHistoricos(errverificados)
	#eliminar archivos utilizados por hamiltonian
	#if len(dfTareas) > 0:
		#naves_usadas = dfTareas.NAVE.unique()
		#for i in naves_usadas:
			#file_ruta = 'rutasAbastos_'+str(i)+'_'+codestr+'.pickle'
			#file_dist = 'distanciasAbastos_'+str(i)+'_'+codestr+'.pickle'
			#util.deleteFile(file_ruta)
			#util.deleteFile(file_dist)

	fin = time.time() - inicio
	print('tiempo utilizado: ' + str(fin))
	logging.info('Tiempo utilizado: '+str(fin))
	print('fin ejecucion')
	logging.info('----FIN EJECUCION----')
#	util.deleteOldFile()
#	util.deleteOldFile("/root/Favorita/Datos/Historicos/")