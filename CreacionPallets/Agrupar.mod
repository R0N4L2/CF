/*********************************************
 * OPL 12.8.0.0 Model
 * Author: lilia
 * Creation Date: 6/02/2019 at 4:56:57 p. m.
 *********************************************/
tuple paramType{
	string PARAMETER;
	float VALUE;
}

{paramType} parametros = ...;

{string} paramName = {p | <p,v> in parametros};
float paramValue[paramName] = [p:v | <p,v> in parametros];

float MAXVOLUME = paramValue["MAXVOLUME"];
float MAXWEIGHT = paramValue["MAXWEIGHT"];
float DISTANCECOST = paramValue["DISTANCECOST"];
int NUMPALLETS = ftoi(paramValue["NUMPALLETS"]);

tuple dataType{
	string barcode;
	int u_manejo;
	int demand;
	float volume;
	float weight;
	float x;
	float y;
	int resistance;
	int pasillo;
	string contamination;
}
{dataType} info_articulos = ...;

{string} barcodes = {b | <b,u,d,v,w,xp,yp,r,p,c> in info_articulos};
int umanejo[barcodes] = [b : u| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
int demand[barcodes] = [b : d| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float volume[barcodes] = [b : v| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float weight[barcodes] = [b : w| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float x[barcodes] = [b : xp| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float y[barcodes] = [b : yp| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
int resistance[barcodes] = [b : r| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
string contamination[barcodes] = [b : c| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
int pasillo[barcodes] = [b : p| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];

{int} pasillos = { p| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos};

float largestX = max(b in barcodes) x[b];
float largestY = max(b in barcodes) y[b];

tuple typeRange{
	int resistance;
	float maxWeight;
	float maxVolume;
	float maxWeightAbove;
}

{typeRange} infoResistances = ...;

{int} resistances = {r | <r,mw,mv,mwa> in infoResistances};
float maxWeight[resistances] = [r : mw | <r,mw,mwv,mwa> in infoResistances];
float maxWeightAbove[resistances] = [r : mwa | <r,mw,mv,mwa> in infoResistances];
float maxVolume[resistances] = [r : mv | <r,mw,mv,mwa> in infoResistances];

//Tuples
tuple contentType{
	int ID_PALLET;
	string CODIGOARTICULO;
	string CODIGOUNIDADMANEJO;
	float CANTIDAD;
}

tuple subpallet{
	int id;
	float volume;
	float weight;
	string contamination;
	float minX;
	float minY;
	float maxX;
	float maxY;
}

//----------------------Sets-----------------------------
//Set subpallets (contains all the characteristics of subpallets)
{subpallet} subpallets = ...;

//Set id subpallets (contains only the id of each subpallet)
{int} idSubpallets = {i.id | i in subpallets};
float volumeSub[idSubpallets] = [i : v | <i,v,w,c,minx,miny,maxx,maxy> in subpallets];
float weightSub[idSubpallets] = [i : w | <i,v,w,c,minx,miny,maxx,maxy>  in subpallets];
string contSub[idSubpallets] = [i : contami | <i,v,p,contami,minx,miny,maxx,maxy>  in subpallets];
float minxSub[idSubpallets] = [i : minx | <i,v,w,c,minx,miny,maxx,maxy> in subpallets];
float minySub[idSubpallets] = [i : miny | <i,v,w,c,minx,miny,maxx,maxy> in subpallets];
float maxxSub[idSubpallets] = [i : maxx | <i,v,w,c,minx,miny,maxx,maxy> in subpallets];
float maxySub[idSubpallets] = [i : maxy | <i,v,w,c,minx,miny,maxx,maxy> in subpallets];

//Set of contents in subpallets
//{contentType} contents = ...;
//Set of pallets

range pallets=1..NUMPALLETS;

//Sets contaminables - contaminantes
{int} contaminables = {i | i in idSubpallets : contSub[i]=="CONTAMINABLE"};
{int} contaminantes = {i | i in idSubpallets : contSub[i]=="CONTAMINANTE"};

tuple infoResistencia{
	int id;
	int resistencia;
	float info;
}

{infoResistencia} infoPeso = ...;
{infoResistencia} infoVolumen = ...;

tuple indexInfo{
	int id;
	int resistencia;
}

{indexInfo} indexResist = {<id,r> | <id,r,info> in infoPeso};
float pesoResistencias[indexResist] = [<id,r> : info | <id,r,info> in infoPeso];
float volResistencias[indexResist] = [<id,r> : info | <id,r,info> in infoVolumen];


//Variables
//assign subpallets to pallets
dvar boolean assign[idSubpallets][pallets];
//assign pallet to task
dvar boolean usedPallet[pallets];
//maximum X distance between products
dvar float+ maxDistanceX[pallets];
//maximum Y distance between products
dvar float+ maxDistanceY[pallets];
//minimum X distance between products
dvar float+ minDistanceX[pallets];
//minimum Y distance between products
dvar float+ minDistanceY[pallets];


// expresiones
dexpr int palletsUsandos = sum(i in pallets)usedPallet[i];

//FO
minimize
  palletsUsandos;

 subject to{
 	//asignar un subpallet a un pallet[
 	forall(j in idSubpallets){
 		sum(i in pallets)assign[j][i] == 1;
 	}
 	//asignar s�lo si se utiliza el pallet
 	forall(j in idSubpallets, i in pallets){
 		assign[j][i]<=usedPallet[i];
 	}
 	//cumplir m�ximo volumen permitido
 	forall(i in pallets){
		maxWeightConst:
		sum(j in idSubpallets)(assign[j][i]*weightSub[j])<=MAXWEIGHT*usedPallet[i];
	}
	//cumplir m�ximo peso permitido
 	forall(i in pallets){
		maxVolConst:
		sum(j in idSubpallets)(assign[j][i]*volumeSub[j])<=MAXVOLUME*usedPallet[i];
	}
	//restriccion de contaminante
	forall(i in pallets, a in contaminables, b in contaminantes){
	  Cont:
	  assign[a][i]+assign[b][i]<=1;
	}
	//maximo peso/volumen permitido por resistencia
	forall(r in resistances, i in pallets){
		maxPesoResis:
		sum(j in idSubpallets) assign[j][i]*pesoResistencias[<j,r>]<=maxWeight[r];
		maxVolResis:
		sum(j in idSubpallets) assign[j][i]*volResistencias[<j,r>]<=maxVolume[r];
	}
	/*
	//set maxX and maxY to zero when the pallt is not used
	forall(j in pallets){
		rMaxX:
		maxDistanceX[j] <= largestX * usedPallet[j];
		rMaxY:
		maxDistanceY[j] <= largestY * usedPallet[j];
		rMinX:
		minDistanceX[j] <= largestX * usedPallet[j];
		rMinY:
		minDistanceY[j] <= largestY * usedPallet[j];
	}

	//the max distance is the largest value for x distance of all the distances that the pallet number visits
	forall(j in pallets, i in subpallets)
	  	maxXT:
		maxDistanceX[j] >= i.maxX * assign[i.id][j];

	//the max distance is the largest value for x distance of all the distances that the pallet number visits
	forall(j in pallets, i in subpallets)
	  	maxYT:
		maxDistanceY[j] >= i.maxY * assign[i.id][j];

	//the min distance is the shortest value for x distance of all the distances that the pallet number visits
	forall(j in pallets, i in subpallets)
	  	a:
		minDistanceX[j] <= largestX * (1 - assign[i.id][j])
							+ i.maxX * assign[i.id][j];

	//the min distance is the shortest value for x distance of all the distances that the pallet number visits
	forall(j in pallets, i in subpallets)
	  	b:
		minDistanceY[j] <= largestY * (1 - assign[i.id][j])
							+ i.maxY * assign[i.id][j];*/
	//cycle-breaking constraints
	forall(j in pallets: j > 1)
	  	cycle:
		usedPallet[j-1] >= usedPallet[j];
}

float sumaW[i in pallets] = sum(j in idSubpallets)(assign[j][i]*weightSub[j]);
float sumaV[i in pallets] = sum(j in idSubpallets)(assign[j][i]*volumeSub[j]);

tuple carateristicas{
	key int ID_PALLET;
	float PESO;
	float VOLUMEN;
}
{carateristicas} Tareas = {<i,sumaW[i],sumaV[i]>|i in pallets : usedPallet[i]>0};

tuple unionType{
	int pallet;
	int subpallet;
}
{unionType} unionPallets = {<j,i> | i in idSubpallets, j in pallets : assign[i][j]==1};
