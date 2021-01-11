
tuple paramType{
	string PARAMETER;
	float VALUE;
}

{paramType} parametros = ...;

{string} paramName = {p | <p,v> in parametros};
float paramValue[paramName] = [p:v | <p,v> in parametros];

float MAXVOLUME = paramValue["MAXVOLUME"];
float MAXWEIGHT = paramValue["MAXWEIGHT"];
float PALLETCOST = paramValue["PALLETCOST"];
float DISTANCECOST = paramValue["DISTANCECOST"];

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
int demand[barcodes] = [b : d| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
int umanejo[barcodes] = [b : u| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float volume[barcodes] = [b : v| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float weight[barcodes] = [b : w| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];


float x[barcodes] = [b : xp| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
float y[barcodes] = [b : yp| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
int resistance[barcodes] = [b : r| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
string contamination[barcodes] = [b : c| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
int pasillo[barcodes] = [b : p| <b,u,d,v,w,xp,yp,r,p,c> in info_articulos];
{int} pasillos = {p | <b,u,d,v,w,xp,yp,r,p,c> in info_articulos};

tuple dualType{
	string barcode;
	float dual;
}
{dualType} infoDuals = ...;
float Duals[barcodes] = [b : du| <b,du> in infoDuals];

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

dvar int+ Use[b in barcodes] in 0..demand[b];
dvar boolean isUsed[barcodes];
dvar boolean usesContaminants;
dvar float+ maxx;
dvar float+ maxy;
dvar float+ minx;
dvar float+ miny;

dvar boolean pasilloUsed[pasillos];
dvar boolean pasilloCompleto[pasillos];

int minResistencia = 10;

execute{
	for(var r in resistances){
		if(r < minResistencia){
			minResistencia = r;
		}
	}
}

dexpr float distance = DISTANCECOST * ((maxx - minx) + (maxy - miny));
//dexpr float costPasillo = 10 * (sum(p in pasillos) pasilloUsed[p]);
dexpr float missing = 2 * sum(b in barcodes) (demand[b] - Use[b] - (1-isUsed[b])*demand[b]);
dexpr float reducePasillo = sum(p in pasillos) pasilloCompleto[p]*10;
/*
execute timeTermination {
    //cplex.tilim = 60; // maximum Runtime = 30 min
    //cplex.epgap = 0.007; // result at gap of 5%   
}*/

execute{
	cplex.epgap = 0.001;
}

minimize
  	PALLETCOST 
  	- sum(b in barcodes) Duals[b] * Use[b] 
  	+ distance
	+ 0.00001*usesContaminants
	- reducePasillo;
	//+ missing;
subject to {
	//do not exceed total weight
	sum(b in barcodes) weight[b] * Use[b] <= MAXWEIGHT;
	
	//do not exceed weight of resistance class
	forall(r in resistances)
		sum(b in barcodes: resistance[b] == r) weight[b] * Use[b] <= maxWeight[r];
		
	//do not exceed weight above
	forall(r in resistances: r > 0)
		sum(b in barcodes: resistance[b] < r) weight[b] * Use[b] <= maxWeightAbove[r];
	
	forall(r in resistances: r > 0)
		sum(b in barcodes: resistance[b] < r) volume[b] * Use[b] <= maxVolume[r];
		
	//do not exceed max volume
	sum(b in barcodes) volume[b] * Use[b] <= MAXVOLUME;
	
	//eliminate either contaminable or contaminante
	forall(b in barcodes: contamination[b] == "CONTAMINANTE")
		isUsed[b] <= usesContaminants;

	//eliminate contaminante or contaminable
	forall(b in barcodes: contamination[b] == "CONTAMINABLE")
		isUsed[b] <= 1 - usesContaminants;
		
	//cannot use if isUsed is false
	forall(b in barcodes){
		Use[b] <= demand[b] * isUsed[b];
		isUsed[b] <= Use[b];
	}
	//if weight and volume not exceeded, all should be in the pallet
	forall(b in barcodes: weight[b]*demand[b] <= MAXWEIGHT && volume[b]*demand[b] <= MAXVOLUME && resistance[b] != minResistencia)
		Use[b] >= isUsed[b] * demand[b];
	
	//define coordinate extreme values
	forall(b in barcodes){
		maxx >= isUsed[b] * x[b];
		maxy >= isUsed[b] * y[b];
		minx <= (1 - isUsed[b]) * largestX + isUsed[b] * x[b];
		miny <= (1 - isUsed[b]) * largestY + isUsed[b] * y[b];
	}

	//Complete
	forall(p in pasillos, b in barcodes : pasillo[b] == p){
		demand[b]*pasilloCompleto[p] <= Use[b];
	}

	forall(p in pasillos) {
		(sum(b in barcodes: pasillo[b]==p)demand[b])*pasilloCompleto[p] <= sum(b in barcodes: pasillo[b]==p)Use[b];
	}
			 
	forall(b in barcodes, p in pasillos: pasillo[b]==p){
		isUsed[b]>=pasilloUsed[p];
		Use[b]<=pasilloUsed[p]*demand[b];
	}
}

tuple content{
	string CODIGOARTICULO;
	int CODIGOUNIDADMANEJO;
	float CANTIDAD;
}

{content} contentsFinal = {<b,umanejo[b],Use[b]> | b in barcodes : isUsed[b]==1};

tuple costType{
	int ID_PALLET;
	float COSTO;
}

{costType} costPallet = {<0,PALLETCOST + distance>};


float sumaW = sum(b in barcodes)(Use[b]*weight[b]);
float sumaV = sum(b in barcodes)(Use[b]*volume[b]);
string contaminacion = "";

execute{
	if(usesContaminants > 0.9){
		contaminacion = "Contaminante";
	} else {
		contaminacion = "Contaminable";
	}
	sumaW;
	sumaV;	
}

tuple infoPalletType{
	float PESO;
	float VOLUMEN;
	string CONTAMINACION;
}

//{infoPalletType} infoPallet = {sumaW, sumaV, contaminacion};