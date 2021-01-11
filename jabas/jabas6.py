# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 21:13:48 2019
@author: Ronald Castillo Capino
@email: ron.h.castillo@gmail.com
"""
from doopl.factory import *
import pandas as pd
import numpy as np
from os.path import dirname, abspath, join
import plotly.express as px
import plotly.offline as offline
from datetime import datetime


def techo(x,dig=3):
    return np.ceil(np.round(x,decimals=dig))
def creacionPallets(modelo,jabas,parametros,tipo="pasillo",paletsPrevios=np.zeros((1,3))):
    with create_opl_model(model=modelo) as opl:
            opl.mute()
            opl.set_input("parametros",parametros)   
            opl.set_input("jabaInformacion",jabas)
            if tipo=="pasillo":
                opl.set_input("palletExtra",paletsPrevios)
            opl.run()
            jabaOutput=opl.get_table("jabasNPallet") 
    return jabaOutput
def FuncionPalletsxJabas(Jabas,parametros,mod,mod1):
    topeMax=np.array([parametros.loc[parametros["parametro"].isin(["pesoMaximo"]),"valor"].iloc[0],parametros.loc[parametros["parametro"].isin(["cantidadJabas","altoMaximo"]),"valor"].prod()])
    colist=['Codigo de Producto','Peso de jaba [kg]','Alto por jabas [m]','Demanda de productos','X[mts]','Y[mts]']
    Jabas=Jabas[colist].astype(float)
    Jabas['Codigo de Producto']=Jabas['Codigo de Producto'].astype(int).astype(str)
    Jabas['Demanda de productos']=Jabas['Demanda de productos'].astype(int)
    Jabas['Peso Demanda']=Jabas[['Peso de jaba [kg]','Demanda de productos']].prod(1)
    Jabas['Alto Demanda']=Jabas[['Alto por jabas [m]','Demanda de productos']].prod(1)
    a=techo((Jabas[['Peso Demanda','Alto Demanda']]%topeMax)/Jabas[['Peso de jaba [kg]','Alto por jabas [m]']].values)
    b=Jabas[['Demanda de productos','Demanda de productos']]-a.values
    b1=b.values*Jabas[['Peso de jaba [kg]','Alto por jabas [m]']]
    c3=np.less_equal(np.multiply(np.floor(b/techo(b1/topeMax).values).fillna(0),Jabas[['Alto por jabas [m]','Peso de jaba [kg]']].values),topeMax[::-1])      
    c4=np.multiply(a,c3.values).replace(0,10**6).min(1).replace(10**6,0)    
    c5=np.less_equal(np.multiply(pd.concat([c4]*2,1).values,Jabas[['Peso de jaba [kg]','Alto por jabas [m]']]),topeMax).all(1)
    Jabas['Demanda Residuo']=c4*c5
    Jabas['Demanda Pallet Enteros']=Jabas['Demanda de productos']-Jabas['Demanda Residuo']
    Jabas['Cantidad Pallet llenos de 1 Producto']=techo(Jabas[['Demanda Pallet Enteros','Demanda Pallet Enteros']]*Jabas[['Peso de jaba [kg]','Alto por jabas [m]']].values/topeMax).max(1)
    Jabas['Jabas por Pallet llenos de 1 Producto']=(Jabas['Demanda Pallet Enteros']/Jabas['Cantidad Pallet llenos de 1 Producto']).fillna(0)
    Jabas1=Jabas.loc[np.less(0,Jabas['Demanda Residuo']),['Codigo de Producto','Peso de jaba [kg]','Alto por jabas [m]','Demanda Residuo','X[mts]','Y[mts]']].rename({'Demanda Residuo':'Demanda de productos'},axis=1) 
    Jabas2=Jabas.loc[np.less(0,Jabas['Cantidad Pallet llenos de 1 Producto']),['Codigo de Producto','Peso de jaba [kg]','Alto por jabas [m]','Cantidad Pallet llenos de 1 Producto','Jabas por Pallet llenos de 1 Producto','X[mts]','Y[mts]']].reset_index(drop=True)
    Jabas2=Jabas2.loc[np.repeat(np.arange(Jabas2.shape[0]),Jabas2['Cantidad Pallet llenos de 1 Producto'].tolist(),axis=0),['Codigo de Producto','Peso de jaba [kg]','Alto por jabas [m]','Jabas por Pallet llenos de 1 Producto','X[mts]','Y[mts]']].rename(columns={'Jabas por Pallet llenos de 1 Producto':'Demanda de productos'}).reset_index(drop=True)
    Jabas1['Peso Demanda']=Jabas1[['Peso de jaba [kg]','Demanda de productos']].prod(1)
    Jabas1['Alto Demanda']=Jabas1[['Alto por jabas [m]','Demanda de productos']].prod(1)
    Jabas1['Demanda SuperPallet']=1
    PalletLlenos=Jabas1.groupby('X[mts]',as_index=False).agg({'Peso Demanda':'sum','Alto Demanda':'sum'})
    PalletLlenos['Cantidad de Pallets lleno por pasillo']=np.floor(PalletLlenos[['Peso Demanda','Alto Demanda']]/topeMax).max(1)
    Xpos=PalletLlenos.loc[np.less(0,PalletLlenos['Cantidad de Pallets lleno por pasillo']),'X[mts]'].tolist()
    dicol={'Codigo de Producto':'codigoJaba','Peso de jaba [kg]':'pesoJaba','Alto por jabas [m]':'alturaJaba','Demanda de productos':'cantidadJabas','X[mts]':'x','Y[mts]':'y'}
    J2=Jabas1.loc[~Jabas1.isin({'X[mts]':Xpos}).any(1),colist].rename(columns=dicol)
    Start=True
    for x in Xpos:
        J1=Jabas1.iloc[np.isin(Jabas1['X[mts]'],x)]
        pallets=PalletLlenos.loc[np.isin(PalletLlenos['X[mts]'],x),'Cantidad de Pallets lleno por pasillo'].values[0]
        if all(np.isin(parametros["parametro"],"PalletTotales",invert=True)):
            parametros=parametros.append(pd.DataFrame({'parametro':'PalletTotales','valor':pallets},index=[0])).reset_index(drop=True)
        else:
            parametros.loc[np.isin(parametros["parametro"],"PalletTotales"),"valor"]=pallets
        jabaOutput=creacionPallets(mod1,J1[['Codigo de Producto','Peso Demanda','Alto Demanda','Demanda SuperPallet','X[mts]','Y[mts]']],parametros[["parametro","valor"]])
        aux=np.isin(J1['Codigo de Producto'],jabaOutput['codigoJaba'])
        Jaux=J1.loc[~aux,colist].rename(columns=dicol)
        Jaux1=J1.loc[aux,colist].rename(columns=dicol)
        pallet=jabaOutput.groupby('codigoPallet',as_index=False).agg({'pesoJaba':'sum','alturaJaba':'sum'}).round(3) 
        pallet[['pesoFaltante','altoFaltante']]=topeMax-pallet[['pesoJaba','alturaJaba']]
        minDims=Jaux[['pesoJaba','alturaJaba']].round(3).min(0).values
        aux=np.less_equal(minDims,pallet[['pesoFaltante','altoFaltante']].values).all(1)
        if any(aux):
            pallet['pesoYalto']=pallet[['pesoFaltante','altoFaltante']].prod(1)
            pallet=pallet.sort_values(by='pesoYalto',ascending=False).reset_index(drop=True)
            pallet['idx']=pallet.index.values+1 
            pal=pallet.loc[aux,['idx','altoFaltante','pesoFaltante']].rename(columns={'idx':'codigoPallet','altoFaltante':'altoPermitido','pesoFaltante':'pesoPermitido'})
            jabaOutput=jabaOutput.merge(pallet[['codigoPallet','idx']],on='codigoPallet')[['codigoJaba','idx']].rename(columns={'idx':'codigoPallet'})
            jabaOutput1=Jaux1.merge(jabaOutput[['codigoJaba','codigoPallet']],on='codigoJaba') 
            jabaOutput=creacionPallets(mod1,Jaux[['codigoJaba','pesoJaba','alturaJaba','cantidadJabas','x','y']],parametros[["parametro","valor"]],"pasillo",pal)
            jabaOutput1=jabaOutput1.append(jabaOutput) 
            pe=jabaOutput.groupby('codigoJaba',as_index=False).agg({'cantidadJabas':'sum'})
            Jaux=Jaux.merge(pe[['codigoJaba','cantidadJabas']],on='codigoJaba',how='left').fillna(0)   
            Jaux['cantidadJabas']=Jaux['cantidadJabas_x']-Jaux['cantidadJabas_y']
            Jaux=Jaux.loc[np.less(0,Jaux['cantidadJabas']),['codigoJaba','pesoJaba','alturaJaba','cantidadJabas','x','y']]
        else:
            jabaOutput1=Jaux1.merge(jabaOutput[['codigoJaba','codigoPallet']],on='codigoJaba') 
        J2=J2.append(Jaux[['codigoJaba','pesoJaba','alturaJaba','cantidadJabas','x','y']])
        if Start:
            jabaOutput2=jabaOutput1
            Start=False
        else:
            jabaOutput1["codigoPallet"]+=jabaOutput2["codigoPallet"].max()
            jabaOutput2=jabaOutput2.append(jabaOutput1)  
    jabaOutput=creacionPallets(mod,J2,parametros[["parametro","valor"]],"nave")
    jabaOutput["codigoPallet"]+=jabaOutput2["codigoPallet"].max()
    jabaOutput2=jabaOutput2.append(jabaOutput)
    Jabas2["codigoPallet"]=Jabas2.index.values+1+jabaOutput2["codigoPallet"].max()
    Jabas2=Jabas2.rename(columns=dicol)
    jabaOutput2=jabaOutput2.append(Jabas2).reset_index(drop=True)
    jabaOutput2=jabaOutput2.sort_values(by=['codigoPallet'])
    return jabaOutput2    
if __name__ == '__main__':
    DATADIR=dirname(abspath('__file__'))
    modelo1=join(DATADIR,"Jabas8.mod")
    modelo=join(DATADIR,"Jabas9.mod")
    data=join(DATADIR,"Jabas.xlsx")
    xl = pd.ExcelFile(data)
    parametros=xl.parse("parametros")
    Jabas=xl.parse("Jabas")    
    locales=Jabas["Local"].drop_duplicates().tolist()
    writer = pd.ExcelWriter("Jabas7.xlsx",engine='xlsxwriter')
    for local in locales:
        ti = datetime.now()
        print(local)
        JabasOutput=FuncionPalletsxJabas(Jabas.iloc[np.isin(Jabas["Local"],local)],parametros,modelo,modelo1)    
        JabasOutput[['codigoJaba','cantidadJabas','alturaJaba','pesoJaba','codigoPallet','x','y']].to_excel(writer, sheet_name=str(local),index=False)
        JabasOutput["codigoPallet"]=JabasOutput["codigoPallet"].astype(int).astype(str)
        offline.init_notebook_mode(connected=True)
        fig=px.scatter(JabasOutput,x="x",y="y",color="codigoPallet",hover_data=['codigoJaba','pesoJaba','alturaJaba','cantidadJabas'],marginal_y="histogram",marginal_x="histogram")
        offline.plot(fig,filename=join(DATADIR,"Jabas_"+str(local)+".html"),auto_open=False,show_link = False)   
        print(datetime.now()-ti)
    writer.save()  