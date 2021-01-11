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
float paramValue[paramName] = [p : v | <p,v> in parametros];

float MAXVOLUME = paramValue["MAXVOLUME_FUR"];
float MAXWEIGHT = paramValue["MAXWEIGHT_FUR"];
float DISTANCECOST = paramValue["DISTANCECOST"];
int NUMPALLETS = ftoi(paramValue["NUMPALLETS"]);
int MAXLEGOS = ftoi(paramValue["MAXLEGOS"]);


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
	int id;
	string barcode;
	string u_manejo;
	float quantity;
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

//Set of contents in subpallets
//{contentType} contents = ...;
//Set of pallets
range pallets=1..NUMPALLETS;
range legos=1..MAXLEGOS;

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

float minResist[idSubpallets];
float maxResist[idSubpallets];

execute{
	for(var i in idSubpallets){
		minResist[i] = 20;
		maxResist[i] = 0;	
	}

	for(var ir in indexResist){
		if(pesoResistencias[ir] > 0 && ir.resistencia < minResist[ir.id]){
			minResist[ir.id] = ir.resistencia;
		}
		if(pesoResistencias[ir] > 0 && ir.resistencia > maxResist[ir.id]){
			maxResist[ir.id] = ir.resistencia;		
		}
	}	
}

float largestX = max(b in barcodes) x[b];
float largestY = max(b in barcodes) y[b];

//Variables
//assign subpallets to pallets
dvar boolean assign[idSubpallets][pallets][legos];
//assign pallet to task
dvar boolean usedPallet[pallets];

//Expresiones
dexpr int palletsUsandos = sum(i in pallets)usedPallet[i];

execute timeTermination {
    cplex.tilim = 180; // maximum Runtime = 3 min
    cplex.epgap = 0.01; // result at gap of 1%   
}

//FO
minimize
  palletsUsandos;

 subject to{
 	//asignar un subpallet a un pallet
 	forall(j in idSubpallets){
 		sum(i in pallets, k in legos)assign[j][i][k] == 1;
 	}
 	//asignar solo si se utiliza el pallet
 	forall(j in idSubpallets, i in pallets, k in legos){
 		assign[j][i][k] <= usedPallet[i];
 	}
	//asignar maximo 3 subpallets a pallet
	forall(i in pallets){
		sum(j in idSubpallets, k in legos) assign[j][i][k] <= 3 * usedPallet[i];
	}
	//se puede asignar maximo una ubicacion
	forall(i in pallets, k in legos)
		sum(j in idSubpallets) assign[j][i][k] <= 1;
		
 	//cumplir maximo volumen permitido
 	forall(i in pallets){
		maxWeightConst:
		sum(j in idSubpallets, k in legos)(assign[j][i][k]*weightSub[j]) <= MAXWEIGHT * usedPallet[i];
	}
	//cumplir maximo peso permitido
 	forall(i in pallets){
		maxVolConst:
		sum(j in idSubpallets, k in legos)(assign[j][i][k]*volumeSub[j]) <= MAXVOLUME * usedPallet[i];
	}
	//restriccion de contaminante
	forall(i in pallets, a in contaminables, b in contaminantes, k1 in legos, k2 in legos){
	  Cont:
	  assign[a][i][k1] + assign[b][i][k2] <= 1;
	}
	//maximo peso/volumen permitido por resistencia
	forall(r in resistances, i in pallets){
		maxPesoResis:
		sum(j in idSubpallets, k in legos) assign[j][i][k] * pesoResistencias[<j,r>] <= maxWeight[r];
		maxVolResis:
		sum(j in idSubpallets, k in legos) assign[j][i][k]*volResistencias[<j,r>] <= maxVolume[r];
	}
	
	//
	forall(j1 in idSubpallets, j2 in idSubpallets, i in pallets, k in legos : k < MAXLEGOS)
		(1 - assign[j1][i][k])*5 + minResist[j1] >= assign[j2][i][k+1]*maxResist[j2];

	forall(j1 in idSubpallets, j2 in idSubpallets, i in pallets, k in legos : k < MAXLEGOS)
		(1 - assign[j1][i][k])*MAXVOLUME + volumeSub[j1] >= assign[j2][i][k+1]*volumeSub[j2];
	
	//cycle-breaking constraints
	forall(j in pallets: j > 1)
	  	cycle:
		usedPallet[j-1] >= usedPallet[j];
		
	forall(i in pallets, k in legos: k>1)
		sum(j in idSubpallets) assign[j][i][k-1] >= sum(j in idSubpallets) assign[j][i][k];
}

float sumaW[i in pallets] = sum(j in idSubpallets, k in legos)(assign[j][i][k]*weightSub[j]);
float sumaV[i in pallets] = sum(j in idSubpallets, k in legos)(assign[j][i][k]*volumeSub[j]);

tuple carateristicas{
	key int ID_PALLET;
	float PESO;
	float VOLUMEN;
}
{carateristicas} Tareas = {<i,sumaW[i],sumaV[i]>|i in pallets : usedPallet[i]>0};

tuple unionType{
	int pallet;
	int subpallet;
	int base;
}
{unionType} unionPallets = {<j,i,k> | i in idSubpallets, j in pallets, k in legos : assign[i][j][k]==1};

execute{unionPallets;}