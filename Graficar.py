import os
import sys
import pdb

#gráficos
import pandas
import matplotlib.pyplot as plt
import pip
import plotly
#librería estadística
import numpy as np
#mapas de calor
import seaborn as sns
import pylab
import matplotlib as mpl
#paletas de colores
import matplotlib.cm as cm
#guardar en formato normal
import plotly.offline as offline

import chart_studio.plotly as py
import plotly.graph_objs as go

import scipy

import networkx

import os


'''
relPathToDatos = "..\\Modelo\\"
if not sys.platform.startswith('win'):
	relPathToDatos = "../Modelo/"
	'''
relPathToDatos=str(os.getcwdb())[2:-1].replace("\\\\","\\")
#Plotly credentials
#Ronald:
plotlykeys=['ron.h.castillo','pphcvGPSf0tbodZnOofm']
class label(object):
	def __init__(self,path,distanceTraveled,weight,volume):
		self.path = path
		self.distanceTraveled = distanceTraveled
		self.weight = weight #this is an array of the weight at each index (0-N) resistance level.
		self.volume = volume
		self.currentLocation = self.getCurrentLocation
		self.MAXWEIGHT = 1000
		self.MAXVOLUME = 2.0
		self.PALLETCOST = 58
		
	def getCurrentLocation(self):
		#
		return None
		
	def getRemainingCBs(self):
		#the remaining CBs are all the CBs that have not been visited that have the same or smaller 
		pass
		
	def getClosestCBs(self):
		pass
	
	
	def getDistances(self):
		#calculate the Manhattan distance from the current location for all the remaining CBs
		pass
		
	@property
	def getWeightAndVolumeLeft(self):
		#calculate the volume left based on the MAXVOLUME and the existingVolume
		#for weight remaining, determine the minimum of the total weight remaining and the weight remaining in the lowest 
		pass

def read_file(fileName):
	if fileName.endswith('.csv'):
		return pandas.read_csv(os.path.join(relPathToDatos,fileName))
	if fileName.endswith('.xlsx'):
		return pandas.read_excel(os.path.join(relPathToDatos,fileName))
		
def eliminateLabels():
	#loop through all the labels to determine which ones should be removed.
	#for a given set of places visited, determine the maximum amount of 
	pass
	
def getDistance(currentX,currentY,nextX,nextY):
	return scipy.sqrt((nextX-currentX)**2 + (nextY - currentY)**2)

def writeln(string):
	f.write(string)
	f.write("\n")

def writeTupleSet(tupleSetName,columns,types,df):
	writeln("{} = {}".format(tupleSetName,'{'))
	for idx, row in df.iterrows():
		rowText = '\t<'
		for colIdx in range(len(columns)):
			if types[colIdx] == 'string':
				if type(row[columns[colIdx]]) is str:
					rowText = rowText + '"' +str(row[columns[colIdx]]) + '",'
				else:
					rowText = rowText + '"' + '{0:.0f}'.format(row[columns[colIdx]]) + '",' #gets rid of trailing 0s
			else:
				rowText = rowText + str(row[columns[colIdx]]) + ','
		rowText = rowText[0:-1] + '>,'
		writeln(rowText)
	writeln("};")
	
def writeArrayData(arrayName,column,df,isString = False,isArray = True):
	if isArray:
		writeln("{} = [".format(arrayName))
	else:
		writeln("{} = {}".format(arrayName,'{'))
	for idx, row in df.iterrows():
		if isString:
			if type(row[column]) is str:
				writeln('\t"{}",'.format(row[column]))
			else:
				writeln('\t"{0:.0f}",'.format(row[column]))
		else:
			writeln('\t{},'.format(row[column]))
		
	if isArray:
		writeln("];")
	else:
		writeln("};")
		
def getXY(nave,pasillo,rack,pasillos):
	try:
		adjPasillo = int(pasillo - 100*int(pasillo/100))
		adjRack = int(rack/10)
		tempDF = pasillos[(pasillos.NAVE == nave) & (pasillos.pasillo == adjPasillo)]
		x0 = tempDF.iloc[0].X
		y0 = tempDF.iloc[0].Y
		r0 = tempDF.iloc[0].rack
		x1 = tempDF.iloc[1].X
		y1 = tempDF.iloc[1].Y
		r1 = tempDF.iloc[1].rack
		pct = (adjRack - r0) / (r1 - r0)
		return x0 + pct * (x1 - x0), y0 + pct * (y1 - y0)
	except:
		return 0,0
		
def getDistances(g):
	distances = {}
	pathDict = dict(networkx.all_pairs_dijkstra_path(g,weight='distance'))
	for start in pathDict.keys():
		if start not in distances.keys():
			distances[start] = {}
		for end in pathDict[start].keys():
			if end != start:
				prev = None
				cumDistance = 0.
				for nextStop in pathDict[start][end]:
					if prev is None:
						pass
					else:
						cumDistance += g.get_edge_data(prev,nextStop)['distance']
						if start == 'cb_7861030531017' and end == 'cb_7861029405299':
							print (prev,nextStop,g.get_edge_data(prev,nextStop)['distance'],cumDistance)
					prev = nextStop
				distances[start][end] = cumDistance
	return distances

def definirOrden(pallets, verificado):
	palletOrden = pallets.sort_values(by=['CODIGODESPACHO','NAVE','ID_PALLET','ORDEN'])
	palletOrden = palletOrden[['CODIGODESPACHO','NAVE','ID_PALLET','ORDEN','CODIGOARTICULO']].merge(verificado[['CODIGOARTICULO','PASILLO','RACK','X','Y']], left_on = ['CODIGOARTICULO'], right_on = ['CODIGOARTICULO'], how = 'left')
	#palletOrden.rename(columns={'PASILLO':'adjPasillo'}, inplace=True)
	#palletOrden.rename(columns={'RACK':'adjRack'}, inplace=True)
	return palletOrden

def filtrarDatos(CODIGODESPACHO, nave, palletOrden, pasillos, finesPasillo, entrada):
	palletNave = palletOrden[(palletOrden.CODIGODESPACHO == CODIGODESPACHO) & (palletOrden.NAVE == nave)].dropna().drop_duplicates()
	pasillosNave = pasillos[pasillos.NAVE == nave].dropna().drop_duplicates()
	finesPasilloNave = finesPasillo[finesPasillo.NAVE == nave].dropna().drop_duplicates()
	#pdb.set_trace()
	entradaNave=entrada[entrada.NAVE==nave][['X','Y','UBICACION']].dropna().drop_duplicates()
	entradaNave.columns = ['entradaX','entradaY','UBICACION']
	
	return palletNave, pasillosNave, finesPasilloNave, entradaNave

def createGraph(pallets, finesPasilloFull, entrada):
	graphs = {}
	pathDict ={}
	distances = {}
	g = networkx.Graph()
	maxPasillo = finesPasilloFull.groupby(by = 'PASILLO').UBICACION.max().reset_index()
	minPasillo = finesPasilloFull.groupby(by = 'PASILLO').UBICACION.min().reset_index()
	#pdb.set_trace()
	specialPasillos = maxPasillo.merge(minPasillo,on=['PASILLO','UBICACION']).PASILLO.values
	finesPasillo = finesPasilloFull[~finesPasilloFull.PASILLO.isin(specialPasillos)]
	#pdb.set_trace()
	#toEntrada = finesPasillo.merge(entrada,how='inner',left_on = 'UBICACION', right_on = 'UBICACION')
	toEntrada = finesPasillo.merge(entrada,how='inner',on='UBICACION')
	for row in toEntrada.itertuples():
		g.add_edge('finPasillo{:d}_{:d}'.format(row.PASILLO, row.UBICACION) , 'entrada', distance = np.sqrt((row.entradaX - row.X)**2+(row.entradaY - row.Y)**2))
		#g.add_edge('finPasillo{}_{}'.format(row.PASILLO, row.UBICACION) , 'entrada', distance = scipy.sqrt((row.entradaX - row.X_CODIGODESPACHO)**2+(row.entradaY - row.Y_CODIGODESPACHO)**2))
	#if there are any special pasillos near the openin, connect each CB to them
	entradaPasillo = finesPasilloFull[(finesPasilloFull.PASILLO.isin(specialPasillos)) & (finesPasilloFull.UBICACION.isin(entrada.UBICACION))].PASILLO.unique()
	#pdb.set_trace()
	for row in pallets[pallets.PASILLO.isin(entradaPasillo)].itertuples():
		for ent in entrada.itertuples(): #should only be one
			g.add_edge('cb_{}'.format(row.CODIGOARTICULO) , 'entrada', distance = np.sqrt((ent.entradaX - row.X)**2+(ent.entradaY - row.Y)**2))

	#add edges from every end of pasillo to every other either becuase they have the same UBICACION or the same pasillo
	#pdb.set_trace()
	#meetUbicacion = finesPasillo.merge(finesPasillo,left_on='UBICACION',right_on='UBICACION')
	meetUbicacion = finesPasillo.merge(finesPasillo,on=['NAVE','UBICACION'])
	meetUbicacion = meetUbicacion[meetUbicacion.PASILLO_x < meetUbicacion.PASILLO_y]
	for row in meetUbicacion.itertuples():
		g.add_edge('finPasillo{:.0f}_{:.0f}'.format(row.PASILLO_x,row.UBICACION),'finPasillo{:.0f}_{:.0f}'.format(row.PASILLO_y,row.UBICACION), distance = np.sqrt((row.X_x - row.X_y)**2+(row.Y_x - row.Y_y)**2))
		#g.add_edge('finPasillo{}_{}'.format(row.PASILLO_x,row.UBICACION), 'finPasillo{}_{}'.format(row.PASILLO_y,row.UBICACION), distance = scipy.sqrt((row.X_CODIGODESPACHO_x - row.X_CODIGODESPACHO_y)**2+(row.Y_CODIGODESPACHO_x - row.Y_CODIGODESPACHO_y)**2))
	#pdb.set_trace()
	#meetPasillo = finesPasillo.merge(finesPasillo,how='inner',left_on='PASILLO',right_on='PASILLO')
	meetPasillo = finesPasillo.merge(finesPasillo,how='inner',on=['PASILLO','NAVE'])
	meetPasillo = meetPasillo[meetPasillo.UBICACION_x < meetPasillo.UBICACION_y]
	for row in meetPasillo.itertuples():
		g.add_edge('finPasillo{:.0f}_{:.0f}'.format(row.PASILLO,row.UBICACION_x),'finPasillo{:.0f}_{:.0f}'.format(row.PASILLO,row.UBICACION_y), distance = np.sqrt((row.X_x - row.X_y)**2+(row.Y_x - row.Y_y)**2))
		#g.add_edge('finPasillo{}_{}'.format(row.PASILLO,row.UBICACION_x), 'finPasillo{}_{}'.format(row.PASILLO,row.UBICACION_y), distance = scipy.sqrt((row.X_CODIGODESPACHO_x - row.X_CODIGODESPACHO_y)**2+(row.Y_CODIGODESPACHO_x - row.Y_CODIGODESPACHO_y)**2))

	#add edges from the CBs in the special pasillos to the end of the pasillos that have the same UBICACION
	finesPasilloSpecial = finesPasilloFull[finesPasilloFull.PASILLO.isin(specialPasillos)]
	#pdb.set_trace()
	#meetUbicacionSpecial = finesPasilloSpecial.merge(finesPasillo,how='inner',left_on='UBICACION',right_on='UBICACION')
	meetUbicacionSpecial = finesPasilloSpecial.merge(finesPasillo,how='inner',on=['NAVE','UBICACION'])
	endOfPasillosToCBInSpecial = pallets[pallets.PASILLO.isin(specialPasillos)].merge(meetUbicacionSpecial,how='inner',left_on=['PASILLO'],right_on=['PASILLO_x'])
	for row in endOfPasillosToCBInSpecial.itertuples():
		#pdb.set_trace()
		#print('finPasillo{}_{}'.format(row.pasillo_y,row.UBICACION), 'cb_{}'.format(row.CODIGOARTICULO), distance = scipy.sqrt((row.X_y - row.X)**2+(row.Y_y - row.Y)**2))
		g.add_edge('finPasillo{:.0f}_{:.0f}'.format(row.PASILLO_y,row.UBICACION), 'cb_{}'.format(row.CODIGOARTICULO), distance = np.sqrt((row.X_y - row.X_x)**2+(row.Y_y - row.Y_x)**2))
		#g.add_edge('finPasillo{}_{}'.format(row.PASILLO_y,row.UBICACION), 'cb_{}'.format(row.CODIGOARTICULO), distance = scipy.sqrt((row.X_CODIGODESPACHO_y - row.X_CODIGODESPACHO_x)**2+(row.Y_CODIGODESPACHO_y - row.Y_CODIGODESPACHO_x)**2))

	demandDF = pallets.groupby(by=['CODIGOARTICULO']).agg({'PASILLO': min, 'X': max, 'Y': max}).reset_index()
	#pdb.set_trace()
	#cbPasillo = demandDF.merge(finesPasillo,how='inner',left_on='PASILLO',right_on='PASILLO')
	cbPasillo = demandDF.merge(finesPasillo,how='inner',on='PASILLO')
	#pdb.set_trace()
	
	for idx,row in cbPasillo.iterrows():
		g.add_edge('finPasillo{:.0f}_{:.0f}'.format(row.PASILLO,row.UBICACION), 'cb_{}'.format(row['CODIGOARTICULO']), distance = np.sqrt((row.X_x - row.X_y)**2+(row.Y_x - row.Y_y)**2))
#		g.add_edge('finPasillo{}_{}'.format(row.PASILLO,row.UBICACION), 'cb_{}'.format(row['CODIGOARTICULO']), distance = scipy.sqrt((row.X_CODIGODESPACHO - row.X)**2+(row.Y_CODIGODESPACHO - row.Y)**2))

	#pdb.set_trace()
	#cb2cb = demandDF.merge(demandDF,how='inner',left_on = 'PASILLO', right_on = 'PASILLO')
	cb2cb = demandDF.merge(demandDF,how='inner',on = 'PASILLO')
	cb2cb = cb2cb[cb2cb['CODIGOARTICULO_x'] < cb2cb['CODIGOARTICULO_y']]
	for idx,row in cb2cb.iterrows():
		#print('cb_{}'.format(row['CODIGOARTICULO_x']), 'cb_{}'.format(row['CODIGOARTICULO_y']), distance = scipy.sqrt((row.X_x - row.X_y)**2+(row.Y_x - row.Y_y)**2))
		g.add_edge('cb_{}'.format(row['CODIGOARTICULO_x']), 'cb_{}'.format(row['CODIGOARTICULO_y']), distance = np.sqrt((row.X_x - row.X_y)**2+(row.Y_x - row.Y_y)**2))
	#pdb.set_trace()
	graphs = g.copy()
	pathDict = dict(networkx.all_pairs_dijkstra_path(g,weight='distance'))
	distances = dict(networkx.all_pairs_dijkstra_path_length(g,weight='distance'))
	return graphs, pathDict, distances

def crearCoordenadas(coordenadasCB, finesPasilloNave):
	#crear coordenadas	
	coordP = {}
	for idx,row in coordenadasCB.iterrows():
		coordP[row.CODIGOARTICULO] = (row.X,row.Y)	
	coordF = {}
	for idx,row in finesPasilloNave.iterrows():
		coordF['finPasillo{:d}_{:d}'.format(int(row.PASILLO),int(row.UBICACION))] = (row.X,row.Y)
	coordP.update(coordF)
	
	return coordP

def crearRutaCompleta(pallet, pathDict,entrada=True):
	#TODO: calcular distancias
	#Incluir distancias desde entrada a primer CB (nodo de entrada: entrada)
	pallet = pallet.reset_index(drop=True)
	completa=[]
	for i in range(pallet.shape[0]):
		if i==0:
			if entrada:
				ruta=pandas.Series(pathDict['entrada'][pallet['CODIGOARTICULO'][i]])
				ruta=ruta[ruta.str.contains('entrada')|ruta.str.contains('finPasillo')|ruta.str.contains(pallet.loc[i,'CODIGOARTICULO'])].tolist()
			else:
				ruta=[pallet['CODIGOARTICULO'][i]]
		else:
			ruta=pandas.Series(pathDict[pallet['CODIGOARTICULO'][i-1]][pallet['CODIGOARTICULO'][i]])
			ruta=ruta[ruta.str.contains('entrada')|ruta.str.contains('finPasillo')|ruta.isin(pallet.loc[i-1:i,'CODIGOARTICULO'].tolist())].tolist()
		if i<pallet.shape[0]-1 and (i>0 or entrada):
			completa+=ruta[:-1]
		elif i==pallet.shape[0]-1:
			completa+=ruta	
	return completa

def distanciaRuta(distances,completa,iniciapasillo=True,finalizapasillo=True):
	#TODO: calcular distancias
	A=pandas.DataFrame.from_dict(distances[completa[0]],orient='index')
	recorrido=iniciapasillo*A[pandas.Series(A.index.tolist()).str.contains('finPasillo').tolist()].min().values[0]
	if len(completa)>1:
		for i in range(len(completa)-1):
			recorrido+=distances[completa[i]][completa[i+1]]	
	A=pandas.DataFrame.from_dict(distances[completa[-1]],orient='index')
	recorrido+=finalizapasillo*A[pandas.Series(A.index.tolist()).str.contains('finPasillo').tolist()].min().values[0]
	return recorrido
def graficarRuta(coordenadasCB, coordenadas, completa, draw, colorRuta,pallet,recorridoPallet):
	#cb = coordenadasCB['CODIGOARTICULO']
	xp = coordenadasCB['X'].tolist()
	yp = coordenadasCB['Y'].tolist()
	index = list(range(1,len(yp)+1))
	edge_trace = go.Scatter(x=[],y=[],mode='lines',legendgroup=str(pallet),name='Pallet '+str(pallet),line=go.scatter.Line(color = colors[colorRuta],shape = 'spline',width = 3))
	coordenadas=pandas.DataFrame(coordenadas)[completa].to_dict(orient='list')
	for i in range(len(completa)-1):
		x0 = coordenadas[completa[i]][0]
		y0 = coordenadas[completa[i]][1]
		x1 = coordenadas[completa[i+1]][0]
		y1 = coordenadas[completa[i+1]][1]
		edge_trace['x'] += (x0, x1)
		edge_trace['y'] += (y0, y1)
		edge_trace['line']['width'] = 2
	draw.append(edge_trace)
	node_trace=go.Scatter(
		x=xp,
		y=yp,
		text=index,
		textfont=dict(color=colors[colorRuta],size=10),
		textposition='bottom center',
		mode='markers+text',
		name='orden SmartBP recorido={:.2f}[m]'.format(recorridoPallet),
		legendgroup=str(pallet),
		hoverinfo='text',
		marker=go.scatter.Marker(color=colors[colorRuta],size=2))
	draw.append(node_trace)	
	return draw

def drawEstantes(finesPasillo,draw):
	A=finesPasillo[finesPasillo.PASILLO<98].groupby(['NAVE','PASILLO','X'],as_index=False).agg({'Y': ['min', 'max']})
	A.columns=['_'.join(list(set(col)-{''})) for col in A.columns.values]
	C=A[['NAVE','X']].drop_duplicates();C1,C2=C.iloc[0:-1].values,C.iloc[1:].values
	C=np.append(C1,(C1+C2)/2,axis=1)
	C=pandas.DataFrame(C[C[:,2]%1==0][:,[0,1,3]])
	C.rename(columns={0:'NAVE',1:'X',2:'ESTANTE'},inplace=True)
	A=A.merge(C,on=['NAVE','X']).sort_values(['NAVE','PASILLO']).drop(['PASILLO','X'],axis=1)
	A['ESTANTE_MIN_X'],A['ESTANTE_MAX_X']=A['ESTANTE'],A['ESTANTE']
	A.rename(columns={'Y_min':'ESTANTE_MIN_Y','Y_max':'ESTANTE_MAX_Y','min_Y':'ESTANTE_MIN_Y','max_Y':'ESTANTE_MAX_Y'},inplace=True)
	A=A.drop(['ESTANTE'],axis=1)
	'''
	A1=finesPasillo[finesPasillo.PASILLO>=98].groupby(['NAVE','PASILLO','Y'],as_index=False).agg({'X': ['min', 'max']})
	A1.columns=['_'.join(list(set(col)-{''})) for col in A1.columns.values]
	A1['ESTANTE_MIN_Y'],A1['ESTANTE_MAX_Y']=A1['Y'],A1['Y']
	A1.rename(columns={'min_X':'ESTANTE_MIN_X','max_X':'ESTANTE_MAX_X'},inplace=True)
	A1=A1.drop(['PASILLO','Y'],axis=1)
	A=pandas.concat([A,A1],sort=True).reset_index(drop=True)'''
	for i in range(A.shape[0]):
		y0,y1,x0,x1=A[['ESTANTE_MIN_Y','ESTANTE_MAX_Y','ESTANTE_MIN_X','ESTANTE_MAX_X']].iloc[i]
		edge_trace=go.Scatter(x=[x0,x1],y=[y0,y1],mode='lines',showlegend=False,line=go.scatter.Line(color='black',shape='spline',width=4))
		draw.append(edge_trace)
	return draw
	

def graficarPlotly(draw, titulo, nombre_archivo,online=False):
	fig=go.Figure(data=draw,
		layout=go.Layout(
			title='<br>' + titulo,
			titlefont=dict(family='Timer New Roman', size=20),
			xaxis=go.layout.XAxis(showgrid = False, zeroline=False, showticklabels=False),
			yaxis=go.layout.YAxis(showgrid = False, zeroline=False, showticklabels=False)
			)
		)
	if online:
		plotly.tools.set_credentials_file(username=plotlykeys[0],api_key=plotlykeys[1])
		py.iplot(fig, filename = nombre_archivo)
	else:
		offline.init_notebook_mode(connected=True)
		offline.plot(fig,filename=os.path.join(relPathToDatos,nombre_archivo[nombre_archivo.find("codigodespacho"):].replace(" ","_")+'.html'),auto_open=False,show_link = False)


def colorBase(siz):
	colores=[]
	for i in range(256**max(3-siz,0),256**3,256**3//(siz+1)):
		colores+=['rgb('+str(i//256**2%256)+','+str(i//256%256)+','+str(i%256)+')']	
	return colores
if __name__ == "__main__":
	
	#Colores para gráfica
	colors = ['green','blue','red','magenta','orange','cyan','lime','yellow','purple','violet','pink','navy','teal','olive','gray','maroon','salmon','gold','dark green','turquoise','dodger blue','indigo',
				'green','blue','red','magenta','orange','cyan','lime','yellow','purple','violet','pink','navy','teal','olive','gray','maroon','salmon','gold','dark green','turquoise','dodger blue','indigo']
	
	
	#colorscale=['rgb(165,0,38)','rgb(215,48,39)','rgb(244,109,67)','rgb(253,174,97)','rgb(254,224,144)']
	
	#lectura de archivos necesarios
	#TODO: Pallets (archivo de salida de modelo de optimización)
	pallets = read_file('tareas_generadas76_1579410000000_PEA_20906_3100.xlsx')
	pallets.CODIGOARTICULO = pallets['CODIGOARTICULO'].astype(str)
	#TODO: Info de artículos
	verificado = read_file('Verificados76_1579410000000_PEA_20906_3100.xlsx')
	verificado =verificado.rename(columns={'X_PASILLO_LOCAL':"X", 'COORDENADAYLOCAL':"Y"})
	verificado.CODIGOARTICULO = verificado['CODIGOARTICULO'].astype(str)
	pallets=pallets.merge(verificado[['CODIGODESPACHO','X', 'Y']],on="CODIGODESPACHO")
	#TODO: Info de pasillos
	pasillos = read_file('pasillos.xlsx')
	#TODO: Info fines de pasillo
	finesPasillo = read_file('finesDePasillo.xlsx')
	#Info entrada
	#------entrada debe modificarse dependiendo de la ubicación a evaluar---
	entrada = pandas.DataFrame.from_dict({'NAVE':[1,2,3,4,5],'X':[5,5,5,5,5],'Y':[0,0,0,0,0],'UBICACION':[1,1,1,1,1]})
	#entrada = pandas.DataFrame.from_dict({'NAVE':[1,2,3,4,5],'X':[5,5,5,5,5],'Y':[150,216,216,150,220],'UBICACION':[5,7,7,5,7]})
	#Info pasillos fisicos
	#estantes = read_file('estanteria.xlsx')
	
	#Organizar orden de picking
	palletOrden = definirOrden(pallets, verificado)
	
	#TODO: definir CODIGODESPACHO de graficas
	codigodespachos=palletOrden.CODIGODESPACHO.drop_duplicates().reset_index(drop=True)
	for codigodespacho in codigodespachos:
		palletOrden1=palletOrden[palletOrden.CODIGODESPACHO==codigodespacho]
		graph_total={}
		distances_total={}
		naves=palletOrden1.NAVE.drop_duplicates().reset_index(drop=True)
		for nave in naves:
			#Info impresion ruta
			draw=[]
			palletNave,pasillosNave,finesPasilloNave,entradaNave=filtrarDatos(codigodespacho, nave, palletOrden1, pasillos, finesPasillo, entrada)
			graphs,pathDict,distances=createGraph(palletNave,finesPasilloNave,entradaNave)
			graph_total[nave] = graphs
			distances_total[nave] = distances		
			id_pallets = palletNave.ID_PALLET.drop_duplicates().reset_index(drop=True)
			recorridoTotal=0
			#colors=colorBase(len(id_pallets))
			for colorRuta,pallet in enumerate(id_pallets):
				print(pallet)
				coordenadasCB = palletNave[palletNave.ID_PALLET==pallet][['CODIGOARTICULO','X','Y']].reset_index(drop=True)
				coordenadasCB.CODIGOARTICULO=coordenadasCB.CODIGOARTICULO.astype(int)		
				coordenadasCB['CODIGOARTICULO'] = list('cb_'+coordenadasCB.CODIGOARTICULO.astype(str))
				coordenadas = crearCoordenadas(coordenadasCB, finesPasilloNave)			
				completa=crearRutaCompleta(coordenadasCB,pathDict,entrada=True)
				recorridoPallet=distanciaRuta(distances,completa,iniciapasillo=True,finalizapasillo=True)
				recorridoTotal+=recorridoPallet
				#inifin=np.where(pandas.Series(completa).str.contains('cb'))[0]
				#completa=completa[inifin[0]:inifin[-1]]
				draw = graficarRuta(coordenadasCB,coordenadas,completa,draw,colorRuta,pallet,recorridoPallet)
			draw = drawEstantes(finesPasilloNave,draw)
			titulo = 'Picking codigodespacho ' + str(codigodespacho) + ' nave ' + str(nave)+' recorrido total de {:.2f}[m]'.format(recorridoTotal)
			nombre_archivo = '(n) Picking codigodespacho ' + str(codigodespacho) + ' nave ' + str(nave)
			#pdb.set_trace()
			graficarPlotly(draw, titulo, nombre_archivo)