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

relPathToOPL = "..\\asignarFurgones\\"
if not sys.platform.startswith('win'):
	relPathToOPL = "../asignarFurgones/"

def readParameters(parametros, furgones, locales, pedidos, proveedores, lista_incompatibles):
	parametros = util.readFile(parametros)
	info_furgones = util.readFile(furgones)
	info_locales = util.readFile(locales)
	info_pedidos = util.readFile(pedidos)
	info_prov = util.readFile(proveedores)
	info_lista_incomp = util.readFile(lista_incompatibles)
	
	return parametros, info_furgones, info_locales, info_pedidos, info_prov, info_lista_incomp

def definirFurgonesGrandes(info_cantidad_furgones):
	maxFurgones = info_cantidad_furgones.copy()
	maxFurgones = maxFurgones.groupby(['TIPO'],as_index=False).CAPACIDAD.max()
	maxFurgones = maxFurgones.merge(info_cantidad_furgones, left_on = ['TIPO','CAPACIDAD'], right_on = ['TIPO','CAPACIDAD'], how = 'left')
	maxFurgones = maxFurgones[['ID','TIPO','CAPACIDAD','CANTIDAD']]
	return maxFurgones
	

def preasignacionFurgones(info_pedidos, info_cantidad_furgones):

	carga = pandas.DataFrame()
	max_cap_furgones = definirFurgonesGrandes(info_cantidad_furgones)
	num_pre = 0

	#caso 1: demanda frios mayor o igual a furgon de max capacidad o demanda total igual a max capacidad
	max_cap_frio = max_cap_furgones.loc[(max_cap_furgones.TIPO=='F')].reset_index(drop=True)
	recorrerFrios = info_pedidos.copy()
	for idx,row in recorrerFrios.iterrows():
		cap_furgon = max_cap_frio.loc[0,'CAPACIDAD']
		cant_furgon = max_cap_frio.loc[0,'CANTIDAD']
		num_furgones_llenos = math.floor(row.FRIOS/cap_furgon)
		if num_furgones_llenos > 0 and cant_furgon > 0:
			rango_furgones = numpy.arange(num_furgones_llenos)
			for r in rango_furgones:
				if cant_furgon > 0:
					nom_furgon = max_cap_frio.loc[0,'ID'] + '_p' + str(num_pre)
					data_furgon = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['F'],'tipoPallet':['F'],'capacidad':[cap_furgon],'cantidad':[cap_furgon]})
					carga = carga.append(data_furgon)
					info_pedidos.loc[idx,'FRIOS'] = info_pedidos.loc[idx,'FRIOS'] - cap_furgon
					info_pedidos.loc[idx,'TOTAL'] = info_pedidos.loc[idx,'TOTAL'] - cap_furgon
					max_cap_frio.loc[0,'CANTIDAD'] = cant_furgon - 1
					info_cantidad_furgones.loc[(info_cantidad_furgones.TIPO == 'F') & (info_cantidad_furgones.CAPACIDAD == cap_furgon), 'CANTIDAD'] = cant_furgon - 1
					num_pre = num_pre + 1
				else:
					break
		elif row.TOTAL == cap_furgon and cant_furgon > 0:
			nom_furgon = max_cap_frio.loc[0,'ID'] + '_p' + str(num_pre)
			data_furgon1 = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['F'],'tipoPallet':['F'],'capacidad':[cap_furgon],'cantidad':[row.FRIOS]})
			data_furgon2 = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['F'],'tipoPallet':['S'],'capacidad':[cap_furgon],'cantidad':[row.SECOS]})
			carga = carga.append(data_furgon1)
			carga = carga.append(data_furgon2)
			info_pedidos = info_pedidos.drop(idx)
			max_cap_frio.loc[0,'CANTIDAD'] = cant_furgon - 1
			info_cantidad_furgones.loc[(info_cantidad_furgones.TIPO == 'F') & (info_cantidad_furgones.CAPACIDAD == cap_furgon), 'CANTIDAD'] = cant_furgon - 1
			num_pre = num_pre + 1	
	
	#caso 2: demanda secos mayor o igual a furgon de max capacidad
	max_cap_seco = max_cap_furgones.loc[(max_cap_furgones.TIPO=='S')].reset_index(drop=True)
	recorrerSecos = info_pedidos.copy()
	for idx,row in recorrerSecos.iterrows():
		cap_furgon = max_cap_seco.loc[0,'CAPACIDAD']
		cant_furgon = max_cap_seco.loc[0,'CANTIDAD']
		num_furgones_llenos = math.floor(row.SECOS/cap_furgon)
		if num_furgones_llenos > 0 and cant_furgon > 0:
			rango_furgones = numpy.arange(num_furgones_llenos)
			for r in rango_furgones:
				if cant_furgon > 0:
					nom_furgon = max_cap_seco.loc[0,'ID'] + '_p' + str(num_pre)
					data_furgon = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['S'],'tipoPallet':['S'],'capacidad':[cap_furgon],'cantidad':[cap_furgon]})
					carga = carga.append(data_furgon)
					info_pedidos.loc[idx,'SECOS'] = info_pedidos.loc[idx,'SECOS'] - cap_furgon
					info_pedidos.loc[idx,'TOTAL'] = info_pedidos.loc[idx,'TOTAL'] - cap_furgon
					max_cap_seco.loc[0,'CANTIDAD'] = cant_furgon - 1
					info_cantidad_furgones.loc[(info_cantidad_furgones.TIPO == 'S') & (info_cantidad_furgones.CAPACIDAD == cap_furgon), 'CANTIDAD'] = cant_furgon - 1
					num_pre = num_pre + 1
				else:
					break

	#caso 4: demanda total es igual a capacidad furgon
	cant_furg_frios = info_cantidad_furgones[info_cantidad_furgones.TIPO == 'F']
	recorrerPedido = info_pedidos.copy()
	recorrer = cant_furg_frios.copy()
	for idx,row in recorrerPedido.iterrows():
		for idx1,row1 in recorrer.iterrows():
			cantidad_ini = cant_furg_frios.loc[idx1,'CANTIDAD']
			if row.TOTAL == row1.CAPACIDAD and cantidad_ini > 0:
				nom_furgon = row1.ID + '_p' + str(num_pre)
				data_furgon1 = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['F'],'tipoPallet':['F'],'capacidad':[row1.CAPACIDAD],'cantidad':[row.FRIOS]})
				data_furgon2 = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['F'],'tipoPallet':['S'],'capacidad':[row1.CAPACIDAD],'cantidad':[row.SECOS]})
				carga = carga.append(data_furgon1)
				carga = carga.append(data_furgon2)
				info_pedidos = info_pedidos.drop(idx)
				cant_furg_frios.loc[(cant_furg_frios.TIPO=='F')&(cant_furg_frios.CAPACIDAD==row1.CAPACIDAD),'CANTIDAD'] = cantidad_ini - 1
				info_cantidad_furgones.loc[(info_cantidad_furgones.TIPO == 'F') & (info_cantidad_furgones.CAPACIDAD == row1.CAPACIDAD), 'CANTIDAD'] = cantidad_ini - 1
				num_pre = num_pre + 1

	recorrerPedido = info_pedidos.copy()
	recorrer = cant_furg_frios.copy()
	for idx,row in recorrerPedido.iterrows():
		for idx1,row1 in recorrer.iterrows():
			cantidad_ini = cant_furg_frios.loc[idx1,'CANTIDAD']
			if row.FRIOS == row1.CAPACIDAD and cantidad_ini > 0:
				nom_furgon = row1.ID + '_p' + str(num_pre)
				data_furgon1 = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['F'],'tipoPallet':['F'],'capacidad':[row1.CAPACIDAD],'cantidad':[row.FRIOS]})
				carga = carga.append(data_furgon1)
				info_pedidos.loc[idx,'FRIOS'] = row.FRIOS - row1.CAPACIDAD
				info_pedidos.loc[idx,'TOTAL'] = row.TOTAL - row1.CAPACIDAD
				cant_furg_frios.loc[(cant_furg_frios.TIPO=='F')&(cant_furg_frios.CAPACIDAD==row1.CAPACIDAD),'CANTIDAD'] = cantidad_ini - 1
				info_cantidad_furgones.loc[(info_cantidad_furgones.TIPO == 'F') & (info_cantidad_furgones.CAPACIDAD == row1.CAPACIDAD), 'CANTIDAD'] = cantidad_ini - 1
				num_pre = num_pre + 1

	recorrerPedido = info_pedidos.copy()
	cant_furg_secos = info_cantidad_furgones[info_cantidad_furgones.TIPO == 'S']
	recorrer = cant_furg_secos.copy()
	for idx,row in recorrerPedido.iterrows():
		for idx1,row1 in recorrer.iterrows():
			cantidad_ini = cant_furg_secos.loc[idx1,'CANTIDAD']
			if row.SECOS == row1.CAPACIDAD and cantidad_ini > 0:
				nom_furgon = row1.ID + '_p' + str(num_pre)
				data_furgon2 = pandas.DataFrame({'local':[row.ID_UOP],'furgon':[nom_furgon],'tipoFurgon':['S'],'tipoPallet':['S'],'capacidad':[row1.CAPACIDAD],'cantidad':[row.SECOS]})
				carga = carga.append(data_furgon2)
				info_pedidos.loc[idx,'SECOS'] = row.SECOS - row1.CAPACIDAD
				info_pedidos.loc[idx,'TOTAL'] = row.TOTAL - row1.CAPACIDAD
				cant_furg_secos.loc[(cant_furg_secos.TIPO=='S')&(cant_furg_secos.CAPACIDAD==row1.CAPACIDAD),'CANTIDAD'] = cantidad_ini - 1
				info_cantidad_furgones.loc[(info_cantidad_furgones.TIPO == 'S') & (info_cantidad_furgones.CAPACIDAD == row1.CAPACIDAD), 'CANTIDAD'] = cantidad_ini - 1
				num_pre = num_pre + 1	
	return carga, info_pedidos, info_cantidad_furgones

def min_capacidad_furgones(pedido, minCapacidad):
	frios = pedido.FRIOS.sum()
	secos = pedido.SECOS.sum()
	
	num_furgones = minCapacidad.copy()

	for idx,row in minCapacidad.iterrows():
		if row.TIPO == 'F':
			cantidad_final= min(row.CANTIDAD,math.ceil(frios/row.CAPACIDAD))
			num_furgones.loc[idx,'CANTIDAD'] = cantidad_final
		else:
			cantidad_final= min(row.CANTIDAD,math.ceil(secos/row.CAPACIDAD))
			num_furgones.loc[idx,'CANTIDAD'] = cantidad_final			
		
	return num_furgones

def crearFurgones(num_furgones):
	lista_furgones = pandas.DataFrame()
	
	for idx,row in num_furgones.iterrows():
		for i in range(row.CANTIDAD):
			nombre = row.TIPO + '_' + str(row.CAPACIDAD) + '_' + str(i)
			lista_furgones = lista_furgones.append(pandas.DataFrame({'ID':[nombre],'TIPO':[row.TIPO],'CAPACIDAD':[row.CAPACIDAD]}))
	
	return lista_furgones

def crearLocalFurgon(info_locales, lista_furgones):
	lista_localFurgon = pandas.DataFrame()
	for idx,row in info_locales.iterrows():
		for idx1,row1 in lista_furgones.iterrows():
			lista_localFurgon = lista_localFurgon.append(pandas.DataFrame({'ID_UOP':[row.ID_UOP],'ID':[row1.ID]}))
	
	return lista_localFurgon

def crearDistancias(info_locales):
	distancias = pandas.DataFrame()
	segunda = info_locales.copy()
	segunda.insert(len(segunda.keys()),'COMPLETO',0)
	for idx,row in segunda.iterrows():
		for idx1,row1 in segunda.iterrows():
			if idx != idx1 and row1.COMPLETO == 0:
				dist = math.sqrt((row.LATITUD - row1.LATITUD)**2 + (row.LONGITUD - row1.LONGITUD)**2)
				distancias = distancias.append(pandas.DataFrame({'LOCAL_1':[row.ID_UOP],'LOCAL_2':[row1.ID_UOP],'DISTANCIA':[dist]}))
		segunda.loc[idx,'COMPLETO'] = 1
		
	return distancias

def asignarNumeroFurgonesOpl(num_furgones_opl,info_locales, info_cantidad_furgones, info_pedidos, param_asignacion):
	reparticion = pandas.DataFrame()
	with create_opl_model(model=num_furgones_opl) as opl:
		opl.mute()
		opl.set_input('parametros',param_asignacion)
		opl.set_input('infoLocales',info_locales[['ID_UOP','LATITUD','LONGITUD','PRECIO','PENAL','SUB_ZONA']])
		opl.set_input('infoFurgones',info_cantidad_furgones)
		opl.set_input('infoPedido',info_pedidos[['ID_UOP', 'FRIOS', 'SECOS', 'TOTAL']])
		opl.setExportExternalData('numFurgones.dat')
		if opl.run():
			solucion = opl.report
			reparticion = solucion['solucion']
			#print(solucion)
		else:
			print('error: Número de furgones')
	
	return reparticion

def definirNumeroFurgones(dist_furgones,info_cantidad_furgones,info_locales):
	subzonas = info_locales.SUB_ZONA.unique()
	num_furgones = pandas.DataFrame()

	for i in subzonas:
		info_sub = info_locales[info_locales.SUB_ZONA==i]
		furgones_sub = dist_furgones[dist_furgones.local.isin(info_sub.ID_UOP)]
		num_furgones_sub = furgones_sub.groupby(['furgon'], as_index=False).cantidad.sum()
		num_furgones_sub = num_furgones_sub.merge(info_cantidad_furgones[['ID','TIPO','CAPACIDAD']],left_on = ['furgon'], right_on = ['ID'], how = 'left')
		num_furgones_sub = num_furgones_sub[['TIPO','CAPACIDAD','cantidad']]
		num_furgones_sub = num_furgones_sub.rename(columns={'cantidad':'CANTIDAD'})
		num_furgones_sub.insert(0,'SUB_ZONA',i)
		num_furgones = num_furgones.append(num_furgones_sub)
	
	return num_furgones

def clusterLocales(info_locales):
	info_cluster = info_locales.copy()
	X = numpy.array(list(zip(info_cluster.LATITUD, info_cluster.LONGITUD))).reshape(len(info_cluster.LATITUD), 2) 
	K = math.ceil(len(info_cluster)/18)
	kmeans_model = KMeans(n_clusters=K).fit(X)
	for i, l in enumerate(kmeans_model.labels_):
		info_cluster.loc[(info_cluster.LATITUD == X[i][0]) & (info_cluster.LONGITUD == X[i][1]),'GRUPO'] = l
	
	print(info_cluster)
	return cluster_locales
	
def asignarGruposOpl(grupos_opl,parametros,info_subzona,lista_distancias,num_furgones_grupo):
	asignacion = pandas.DataFrame()
	with create_opl_model(model=grupos_opl) as opl:
		#opl.mute()
		opl.set_input('parametros',parametros)
		opl.set_input('infoLocales',info_subzona[['ID_UOP','LATITUD','LONGITUD','PRECIO','PENAL','SUB_ZONA']])
		opl.set_input('infoDistancias',lista_distancias)
		opl.set_input('infoFurgones',num_furgones_grupo)
		opl.setExportExternalData('asignarGrupos.dat')
		if opl.run():
			solucion = opl.report
			#print(solucion)
			asignacion = solucion['solucion']
		else:
			print('error: Grupos')
		
	return asignacion

def asignarFurgonesOpl(furgones_opl,parametros,info_subzona,pedido_sub,lista_furgones,info_prov_sub,lista_localFurgon,sub_incompatibles,lista_distancias):
	asignacion = pandas.DataFrame()
	carga_furgon = pandas.DataFrame()
	with create_opl_model(model=furgones_opl) as opl:
		#opl.mute()
		opl.set_input('parametros',parametros)
		opl.set_input('infoLocales',info_subzona[['ID_UOP','LATITUD','LONGITUD','PRECIO','PENAL','SUB_ZONA']])
		opl.set_input('infoFurgones',lista_furgones)
		opl.set_input('infoPedido',pedido_sub[['ID_UOP', 'FRIOS', 'SECOS', 'TOTAL']])
		opl.set_input('infoProveedores',info_prov_sub[['ID', 'LATITUD', 'LONGITUD', 'PRECIO', 'TIPO_FURGON', 'CANTIDAD']])
		opl.set_input('localFurgon',lista_localFurgon)
		opl.set_input('localesIncompatibles',sub_incompatibles)
		opl.set_input('infoDistancias',lista_distancias)
		opl.setExportExternalData('asignarFurgones.dat')

		if opl.run():
			solucion = opl.report
			#print(solucion)
			asignacion = solucion['asignacion']
			carga_furgon = solucion['carga']
		else:
			print('error: Asignacion furgones')
		
	return asignacion, carga_furgon
	
def asignarIDFurgon(carga_furgon_total,info_furgones,info_locales,por_zonas):

	asignacionID = carga_furgon_total.copy()
	asignacionID.insert(len(asignacionID.keys()),'ID_FURGON','')
	if por_zonas == 0:
		ocuparFurgon = info_furgones.copy()
		ocuparFurgon.insert(len(ocuparFurgon.keys()),'OCUPADO',0)
		for idx,row in carga_furgon_total.iterrows():
			if asignacionID.loc[idx,'ID_FURGON'] == '':
				recorrerFurgon = ocuparFurgon[(ocuparFurgon.TIPO == row.tipoFurgon) & (ocuparFurgon.CAPACIDAD == row.capacidad) & (ocuparFurgon.OCUPADO == 0)].reset_index()
				try:
					asignacionID.loc[((asignacionID.subzona == row.subzona) & (asignacionID.furgon == row.furgon)), 'ID_FURGON'] = recorrerFurgon['ID_FURGON'][0]
					ocuparFurgon.loc[ocuparFurgon.ID_FURGON == recorrerFurgon['ID_FURGON'][0],'OCUPADO'] = 1
				except:
					print('error: Asignacion furgon a local')
					pdb.set_trace()
	else:
		ocuparFurgon = info_furgones.copy()
		ocuparFurgon.insert(len(ocuparFurgon.keys()),'OCUPADO',0)
		asignacionID = asignacionID.merge(info_locales[['ID_UOP','PRIORIDAD']], left_on=['local'], right_on=['ID_UOP'], how='left')
		prioridades = asignacionID.PRIORIDAD.unique()
		prioridades.sort()

		for i in prioridades:
			asignacion_prioridad = asignacionID[asignacionID.PRIORIDAD == i]
			for idx,row in asignacion_prioridad.iterrows():
				if asignacionID.loc[idx,'ID_FURGON'] == '':
					recorrerFurgon = ocuparFurgon[(ocuparFurgon.TIPO == row.tipoFurgon) & (ocuparFurgon.CAPACIDAD == row.capacidad) & (ocuparFurgon.OCUPADO == 0)].reset_index()
					try:
						asignacionID.loc[((asignacionID.subzona == row.subzona) & (asignacionID.furgon == row.furgon)), 'ID_FURGON'] = recorrerFurgon['ID_FURGON'][0]
						ocuparFurgon.loc[ocuparFurgon.ID_FURGON == recorrerFurgon['ID_FURGON'][0],'OCUPADO'] = 1
					except:
						print('error: Asignacion furgon a local')
			ocuparFurgon = ocuparFurgon.sort_values(by=['OCUPADO'])
			ocuparFurgon['OCUPADO'] = 0
	
	return asignacionID

def asignarFurgonEnvio(asignacionID,info_furgones,info_cantidad_furgones):
	nueva_asignacion = pandas.DataFrame()
	agrupar_asignacion = asignacionID.groupby(['ID_FURGON','capacidad','tipoFurgon'], as_index=False).cantidad.sum()
	disp_furgones = info_furgones[~info_furgones.ID_FURGON.isin(agrupar_asignacion.ID_FURGON)]
	asignado = agrupar_asignacion[(agrupar_asignacion.capacidad-agrupar_asignacion.cantidad)==0]
	num_asignado = asignacionID[['ID_FURGON','tipoFurgon','capacidad']].drop_duplicates()
	num_asignado = num_asignado.groupby(['tipoFurgon','capacidad'],as_index=False).ID_FURGON.count()
	reasignar = agrupar_asignacion[(agrupar_asignacion.capacidad-agrupar_asignacion.cantidad)>0]
	info_resumen = info_furgones.groupby(['TIPO','CAPACIDAD'],as_index=False).ID_FURGON.count()
	info_resumen = info_resumen.merge(num_asignado,left_on = ['TIPO','CAPACIDAD'] , right_on = ['tipoFurgon','capacidad'], how = 'left')
	info_resumen = info_resumen.fillna(0)
	info_resumen['disponible'] = (info_resumen.ID_FURGON_x - info_resumen.ID_FURGON_y)
	info_resumen = info_resumen[['TIPO','CAPACIDAD','disponible']]
	
	reasignar_frios = reasignar[reasignar.tipoFurgon=='F']
	reasignar_frios['dif_actual'] = reasignar_frios.capacidad - reasignar_frios.cantidad	
	asignado_frios = pandas.DataFrame()
	pendientes = reasignar_frios.copy()
	while len(pendientes) > 0:
		info_resumen_frios = info_cantidad_furgones[info_cantidad_furgones.TIPO=='F']
		for idx,row in info_resumen_frios.iterrows():
			nom_col = row.TIPO+'_'+str(row.CAPACIDAD)
			if row.CANTIDAD > 0:
				reasignar_frios[nom_col] = row.CAPACIDAD - reasignar_frios.cantidad
				reasignar_frios.loc[(reasignar_frios[nom_col]<0),nom_col] = 50
			else:
				reasignar_frios[nom_col] = 50
		
		clase_furgon = reasignar_frios.columns[4:]
		min_valor = reasignar_frios.loc[:,clase_furgon].values.argmin(axis=1)
		nuevo_furgon = clase_furgon[min_valor]
		reasignar_frios_df = pandas.DataFrame({'ID_FURGON':reasignar_frios['ID_FURGON'],'nuevo_furgon':nuevo_furgon})
		reasignar_frios_df = reasignar_frios_df.merge(info_cantidad_furgones[['ID','TIPO','CAPACIDAD']], left_on=['nuevo_furgon'], right_on=['ID'],how='left')
		reasignar_frios_df['NUEVO_ID'] = ''
		
		reasignar_frios_df.loc[reasignar_frios_df.nuevo_furgon=='dif_actual','NUEVO_ID'] = reasignar_frios_df.ID_FURGON
		reasignar_frios_df = reasignar_frios_df[~reasignar_frios_df.NUEVO_ID.str.contains('F')]
		pendientes = reasignar_frios_df.copy()
		
		for idx,row in pendientes.iterrows():
			disponibles = disp_furgones[(disp_furgones.TIPO==row.TIPO)&(disp_furgones.CAPACIDAD==row.CAPACIDAD)].reset_index(drop=True)
			index = info_cantidad_furgones[(info_cantidad_furgones.TIPO==row.TIPO)&(info_cantidad_furgones.CAPACIDAD==row.CAPACIDAD)].index
			cantidad_disp = info_cantidad_furgones.loc[index[0],'CANTIDAD']
			if len(disponibles)>0 and cantidad_disp>0:
				reasignar_frios_df.loc[idx,'NUEVO_ID'] = disponibles.loc[0,'ID_FURGON']
				disp_furgones = disp_furgones[disp_furgones.ID_FURGON != disponibles.loc[0,'ID_FURGON']]
				info_cantidad_furgones.loc[index,'CANTIDAD'] = cantidad_disp - 1
				pendientes = pendientes[pendientes.ID_FURGON != reasignar_frios_df.loc[idx,'ID_FURGON']]
				reasignar_frios = reasignar_frios[reasignar_frios.ID_FURGON != reasignar_frios_df.loc[idx,'ID_FURGON']]
				asignado_frios = asignado_frios.append(reasignar_frios_df.loc[idx])	

	reasignar_secos = reasignar[reasignar.tipoFurgon=='S'] 
	reasignar_secos['dif_actual'] = reasignar_secos.capacidad - reasignar_secos.cantidad
	asignado_secos = pandas.DataFrame()
	pendientes = reasignar_secos.copy()
	while len(pendientes) > 0:
		info_resumen_secos = info_cantidad_furgones[info_cantidad_furgones.TIPO=='S']
		for idx,row in info_resumen_secos.iterrows():
			nom_col = row.TIPO+'_'+str(row.CAPACIDAD)
			if row.CANTIDAD > 0:
				reasignar_secos[nom_col] = row.CAPACIDAD - reasignar_secos.cantidad
				reasignar_secos.loc[(reasignar_secos[nom_col]<0),nom_col] = 50
			else:
				reasignar_secos[nom_col] = 50
		
		clase_furgon = reasignar_secos.columns[4:]
		min_valor = reasignar_secos.loc[:,clase_furgon].values.argmin(axis=1)
		nuevo_furgon = clase_furgon[min_valor]
		reasignar_secos_df = pandas.DataFrame({'ID_FURGON':reasignar_secos['ID_FURGON'],'nuevo_furgon':nuevo_furgon})
		reasignar_secos_df = reasignar_secos_df.merge(info_cantidad_furgones[['ID','TIPO','CAPACIDAD']], left_on=['nuevo_furgon'], right_on=['ID'],how='left')
		reasignar_secos_df['NUEVO_ID'] = ''
		
		reasignar_secos_df.loc[reasignar_secos_df.nuevo_furgon=='dif_actual','NUEVO_ID'] = reasignar_secos_df.ID_FURGON
		reasignar_secos_df = reasignar_secos_df[~reasignar_secos_df.NUEVO_ID.str.contains('S')]
		pendientes = reasignar_secos_df.copy()
		
		for idx,row in pendientes.iterrows():
			disponibles = disp_furgones[(disp_furgones.TIPO==row.TIPO)&(disp_furgones.CAPACIDAD==row.CAPACIDAD)].reset_index(drop=True)
			index = info_cantidad_furgones[(info_cantidad_furgones.TIPO==row.TIPO)&(info_cantidad_furgones.CAPACIDAD==row.CAPACIDAD)].index
			cantidad_disp = info_cantidad_furgones.loc[index[0],'CANTIDAD']
			if len(disponibles)>0 and cantidad_disp>0:
				reasignar_secos_df.loc[idx,'NUEVO_ID'] = disponibles.loc[0,'ID_FURGON']
				disp_furgones = disp_furgones[disp_furgones.ID_FURGON!=disponibles.loc[0,'ID_FURGON']]
				info_cantidad_furgones.loc[index,'CANTIDAD'] = cantidad_disp - 1
				pendientes = pendientes[pendientes.ID_FURGON != reasignar_secos_df.loc[idx,'ID_FURGON']]
				reasignar_secos = reasignar_secos[reasignar_secos.ID_FURGON != reasignar_secos_df.loc[idx,'ID_FURGON']]
				asignado_secos = asignado_secos.append(reasignar_secos_df.loc[idx])
	
	nueva_asignacion = asignacionID.copy()
	for idx,row in asignado_frios.iterrows():
		nueva_asignacion = nueva_asignacion.replace(row.ID_FURGON,row.NUEVO_ID)
	
	for idx,row in asignado_secos.iterrows():
		nueva_asignacion = nueva_asignacion.replace(row.ID_FURGON,row.NUEVO_ID)
	
	nueva_asignacion = nueva_asignacion[['subzona', 'local', 'tipoPallet','cantidad', 'ID_FURGON']]
	nueva_asignacion = nueva_asignacion.merge(info_furgones[['ID_FURGON','TIPO','CAPACIDAD']], left_on=['ID_FURGON'], right_on=['ID_FURGON'], how = 'left')
	
	
	return nueva_asignacion

def main(parametros,furgones, locales, pedidos, proveedores, lista_incompatibles):
	
	inicio = time.time()
	
	parametros, info_furgones, info_locales, info_pedidos, info_prov, info_lista_incomp = readParameters(parametros,furgones, locales, pedidos, proveedores, lista_incompatibles)
	oplNumFurgones = os.path.join(relPathToOPL,'numeroFurgones.mod')
	oplFurgones = os.path.join(relPathToOPL,'Furgones.mod')
	oplGrupos = os.path.join(relPathToOPL,'dividirSubzona.mod')
	
	minCapacidad = info_furgones.groupby(['TIPO','CAPACIDAD'],as_index=False).ID_FURGON.count()
	minCapacidad = minCapacidad.rename(columns={'ID_FURGON':'CANTIDAD'})
	
	info_cantidad_furgones = minCapacidad.copy()
	capacidad_str = info_cantidad_furgones.CAPACIDAD.astype(str)
	info_cantidad_furgones.insert(0,'ID',info_cantidad_furgones.TIPO+'_'+capacidad_str)
	info_cantidad_furgones = info_cantidad_furgones.sort_values(by=['TIPO','CAPACIDAD'],ascending= [True,False])
	info_cantidad_furgones.insert(0,'INDICE',numpy.arange(len(info_cantidad_furgones)))
	min_frio = info_cantidad_furgones[info_cantidad_furgones.TIPO=='F'].INDICE.min()
	df_frio = pandas.DataFrame({'nombre':'MIN_FRIO','valor':[min_frio]})
	min_seco = info_cantidad_furgones[info_cantidad_furgones.TIPO=='S'].INDICE.min()
	df_seco = pandas.DataFrame({'nombre':'MIN_SECO','valor':[min_seco]})
	param_asignacion = pandas.DataFrame()
	param_asignacion = param_asignacion.append(df_frio)
	param_asignacion = param_asignacion.append(df_seco)
	
	asignacion_total = pandas.DataFrame()
	carga_furgon_total = pandas.DataFrame()
	
	max_num = 190
	max_locales = 12
	max_furgones = 24
	por_zonas = 0	

	dist_furgones = asignarNumeroFurgonesOpl(oplNumFurgones,info_locales, info_cantidad_furgones, info_pedidos, param_asignacion)
	if len(dist_furgones)>0:
		num_furgones_total = definirNumeroFurgones(dist_furgones,info_cantidad_furgones,info_locales)
		furgones_seleccionados = dist_furgones.furgon.unique()
		info_cantidad_furgones_pre = info_cantidad_furgones[info_cantidad_furgones.ID.isin(furgones_seleccionados)]

		#pre asignacion de furgones completos
		pre_carga, info_pedidos, info_cantidad_furgones_pre = preasignacionFurgones(info_pedidos, info_cantidad_furgones_pre)
		#pdb.set_trace()
		info_pedidos['TOTAL'] = info_pedidos.FRIOS + info_pedidos.SECOS
		
		if len(pre_carga) > 0:
			pre_carga = pre_carga.merge(info_locales[['ID_UOP','SUB_ZONA']], left_on = ['local'], right_on = ['ID_UOP'], how = 'left')
			pre_carga = pre_carga.rename(columns={'SUB_ZONA':'subzona'})
			pre_carga = pre_carga[['subzona','local','furgon','tipoFurgon','tipoPallet','capacidad','cantidad']]
			carga_furgon_total = carga_furgon_total.append(pre_carga)
		
		#pdb.set_trace()
		info_cantidad_furgones.loc[(info_cantidad_furgones.ID.isin(info_cantidad_furgones_pre.ID)),'CANTIDAD'] = info_cantidad_furgones_pre.CANTIDAD
		
		dist_furgones = asignarNumeroFurgonesOpl(oplNumFurgones,info_locales, info_cantidad_furgones, info_pedidos, param_asignacion)
		num_furgones_total = definirNumeroFurgones(dist_furgones,info_cantidad_furgones,info_locales)
	
	else:
		por_zonas = 1
		zonas = info_locales.NOM_ZONA_SMX.unique()
		dist_furgones = pandas.DataFrame()
		for zona in zonas:
			info_zona = info_locales[info_locales.NOM_ZONA_SMX==zona]
			pedido_zona = info_pedidos[info_pedidos.ID_UOP.isin(info_zona.ID_UOP)]
			locales_real = pedido_zona.ID_UOP.unique()
			info_zona = info_zona[info_zona.ID_UOP.isin(locales_real)]
			num_furgones_zona = asignarNumeroFurgonesOpl(oplNumFurgones,info_zona, info_cantidad_furgones, pedido_zona, param_asignacion)
			dist_furgones = dist_furgones.append(num_furgones_zona)
			
		num_furgones_total = definirNumeroFurgones(dist_furgones,info_cantidad_furgones,info_locales)
		furgones_seleccionados = dist_furgones.furgon.unique()
		info_cantidad_furgones_pre = info_cantidad_furgones[info_cantidad_furgones.ID.isin(furgones_seleccionados)]

		#pre asignacion de furgones completos
		pre_carga, info_pedidos, info_cantidad_furgones_pre = preasignacionFurgones(info_pedidos, info_cantidad_furgones_pre)
		info_pedidos['TOTAL'] = info_pedidos.FRIOS + info_pedidos.SECOS

		if len(pre_carga) > 0:
			pre_carga = pre_carga.merge(info_locales[['ID_UOP','SUB_ZONA']], left_on = ['local'], right_on = ['ID_UOP'], how = 'left')
			pre_carga = pre_carga.rename(columns={'SUB_ZONA':'subzona'})
			pre_carga = pre_carga[['subzona','local','furgon','tipoFurgon','tipoPallet','capacidad','cantidad']]
			carga_furgon_total = carga_furgon_total.append(pre_carga)		
		
		info_cantidad_furgones.loc[(info_cantidad_furgones.ID.isin(info_cantidad_furgones_pre.ID)),'CANTIDAD'] = info_cantidad_furgones_pre.CANTIDAD
		dist_furgones = pandas.DataFrame()
		for zona in zonas:
			info_zona = info_locales[info_locales.NOM_ZONA_SMX==zona]
			pedido_zona = info_pedidos[info_pedidos.ID_UOP.isin(info_zona.ID_UOP)]
			locales_real = pedido_zona.ID_UOP.unique()
			info_zona = info_zona[info_zona.ID_UOP.isin(locales_real)]
			num_furgones_zona = asignarNumeroFurgonesOpl(oplNumFurgones,info_zona, info_cantidad_furgones, pedido_zona, param_asignacion)
			dist_furgones = dist_furgones.append(num_furgones_zona)
			
		num_furgones_total = definirNumeroFurgones(dist_furgones,info_cantidad_furgones,info_locales)
		furgones_seleccionados = dist_furgones.furgon.unique()
		info_cantidad_furgones = info_cantidad_furgones[info_cantidad_furgones.ID.isin(furgones_seleccionados)]


	subzonas = info_locales.SUB_ZONA.unique()
	#subzonas = subzonas[]
	for i in subzonas:
		print(i)
		info_subzona = info_locales[info_locales.SUB_ZONA==i]
		pedido_sub = info_pedidos[info_pedidos.ID_UOP.isin(info_subzona.ID_UOP)]
		locales_real = pedido_sub.ID_UOP.unique()
		info_subzona  = info_subzona[info_subzona.ID_UOP.isin(locales_real)]
		sub_incompatibles = info_lista_incomp[info_lista_incomp.LOCAL_1.isin(info_subzona.ID_UOP)]
		info_prov_sub = info_prov[info_prov.SUB_ZONA==i]
		num_furgones = num_furgones_total[num_furgones_total.SUB_ZONA==i]
		#num_furgones = min_capacidad_furgones(pedido_sub, minCapacidad)
		lista_furgones = crearFurgones(num_furgones)
		lista_localFurgon = crearLocalFurgon(info_subzona, lista_furgones)
		num_var = len(lista_localFurgon)
		if len(lista_localFurgon) > max_num :
		#if len(info_subzona) > max_num :
			#continue
			parametros_cluster = pandas.DataFrame()
			num_grupos = math.ceil(len(lista_localFurgon)/max_num)
			#num_grupos = math.ceil(len(info_subzona)/max_num)
			num_locales_cluster = max_locales
			num_furgones_cluster = max_furgones
			parametros_cluster = parametros_cluster.append(pandas.DataFrame({'NOMBRE':'NUM_GRUPOS','VALOR':[num_grupos]}))
			parametros_cluster = parametros_cluster.append(pandas.DataFrame({'NOMBRE':'MAX_LOCAL','VALOR':[num_locales_cluster]}))
			parametros_cluster = parametros_cluster.append(pandas.DataFrame({'NOMBRE':'MAX_FURGON','VALOR':[num_furgones_cluster]}))
			lista_distancias = crearDistancias(info_subzona)
			num_furgones_grupo = dist_furgones[dist_furgones.local.isin(locales_real)]
			num_furgones_grupo = num_furgones_grupo.groupby(['local'],as_index=False).cantidad.sum()
			grupos = asignarGruposOpl(oplGrupos,parametros_cluster,info_subzona,lista_distancias,num_furgones_grupo)
			num_grupos = grupos.grupo.unique()
			for j in num_grupos:
				locales_grupo = grupos[grupos.grupo == j]['local']
				info_grupo = info_subzona[info_subzona.ID_UOP.isin(locales_grupo)]
				pedido_grupo = info_pedidos[info_pedidos.ID_UOP.isin(locales_grupo)]
				sub_incompatibles = info_lista_incomp[info_lista_incomp.LOCAL_1.isin(info_grupo.ID_UOP)]
				info_prov_sub = info_prov[info_prov.SUB_ZONA == i]
				dist_furgones_grupo = dist_furgones[dist_furgones.local.isin(locales_grupo)]
				num_furgones_grupo = definirNumeroFurgones(dist_furgones_grupo,info_cantidad_furgones,info_grupo)
				lista_furgones = crearFurgones(num_furgones_grupo)
				lista_localFurgon = crearLocalFurgon(info_grupo, lista_furgones)
				if len(info_grupo) > 1:
					lista_distancias = crearDistancias(info_grupo)
				asignacion, carga_furgon = asignarFurgonesOpl(oplFurgones,parametros,info_grupo,pedido_grupo,lista_furgones,info_prov_sub,lista_localFurgon,sub_incompatibles,lista_distancias)
				carga_furgon.insert(0,'subzona',i+'_'+str(j))
				#pdb.set_trace()
				carga_furgon_total = carga_furgon_total.append(carga_furgon)
		else:
			lista_distancias = pandas.DataFrame(columns=['local1', 'local2', 'distancia'])
			if len(info_subzona) > 1:
				lista_distancias = crearDistancias(info_subzona)
			#pdb.set_trace()
			asignacion, carga_furgon = asignarFurgonesOpl(oplFurgones,parametros,info_subzona,pedido_sub,lista_furgones,info_prov_sub,lista_localFurgon,sub_incompatibles,lista_distancias)
			carga_furgon.insert(0,'subzona',i)
			carga_furgon_total = carga_furgon_total.append(carga_furgon)

	carga_furgon_total = carga_furgon_total.reset_index(drop=True)
	asignacionID = asignarIDFurgon(carga_furgon_total,info_furgones,info_locales,por_zonas)
	asignacionID = asignarFurgonEnvio(asignacionID,info_furgones,info_cantidad_furgones)
	asignacionID.to_excel('asignacionFurgon.xlsx')
	fin = time.time() - inicio
	print('tiempo utilizado: '+str(fin))
if __name__ == "__main__":
	main('parametros_furgones.xlsx','furgones.xlsx','locales.xlsx','pedido_20180313.xlsx','proveedores.xlsx','pares_incompatibles.xlsx')