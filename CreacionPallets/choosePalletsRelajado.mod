
tuple dataType{
	string barcode;
	int u_manejo;
	int demand;
	float weight;
	float volume;
	string contamination;
	float x;
	float y;
}

{dataType} info_articulos = ...;

{string} barcodes = {b | <b,u,d,w,v,c,x,y> in info_articulos};
int demand[barcodes] = [b : d | <b,u,d,w,v,c,x,y> in info_articulos];
int umanejo[barcodes] = [b : u | <b,u,d,w,v,c,x,y> in info_articulos];
float volume[barcodes] = [b : v | <b,u,d,w,v,c,x,y> in info_articulos];
float weight[barcodes] = [b : w | <b,u,d,w,v,c,x,y> in info_articulos];
float x[barcodes] = [b : posx | <b,u,d,w,v,c,posx,posy> in info_articulos];
float y[barcodes] = [b : posy | <b,u,d,w,v,c,posx,posy> in info_articulos];
string contamination[barcodes] = [b : c | <b,u,d,w,v,c,posx,posy> in info_articulos];

tuple patternType{
   int ID_PALLET;
   string CODIGOARTICULO;
   int CODIGOUNIDADMANEJO;
   float CANTIDAD;
}

{patternType} patterns = ...;

tuple patternCostType{
	int ID_PALLET;
	float COSTO;
}

{patternCostType} patternCost = ...;
{int} patternIDs = {i | <i,c> in patternCost};

//float patternItems[i in patternIDs] = sum(<i,b,u,q> in patterns) 1;
float patternWeight[i in patternIDs] = sum(<i,b,u,q> in patterns) q*weight[b];
float patternVolume[i in patternIDs] = sum(<i,b,u,q> in patterns) q*volume[b];

//Variables de decision
dvar float cut[patternCost] in 0..100;
dvar float surplus[b in barcodes] in 0..demand[b]*2;

//Funcion objetiva
minimize
  sum( <p,c> in patternCost ) (c * cut[<p,c>]);

//Restricciones
subject to {
  
	forall( b in barcodes ) 
	   ctFill:
		 sum(<p,c> in patternCost, <p,b,u,q> in patterns) 
			q*cut[<p,c>] >= demand[b];

	forall( b in barcodes ) 
	   ctSurplus:
		 (sum(<p,c> in patternCost, <p,b,u,q> in patterns) q*cut[<p,c>]) - demand[b] == surplus[b];
}

tuple duals{
	string barcode;
	float dualValue;
}

{duals} fillDuals ={};
{duals} surplusVar = {};
//{duals} fillDuals = {<i,ctFill[i].dual>|i in barcodes};
{patternType} contentsFinal = {<i.ID_PALLET,p.CODIGOARTICULO,umanejo[p.CODIGOARTICULO],p.CANTIDAD> | i in patternCost, p in patterns : cut[i]>0 && p.ID_PALLET==i.ID_PALLET};

tuple carateristicas{
	key int ID_PALLET;
	float PESO;
	float VOLUMEN;
	float quantityCuts;
}

{carateristicas} Tareas = {<i.ID_PALLET,patternWeight[i.ID_PALLET],patternVolume[i.ID_PALLET],cut[i]>|i in patternCost, p in patterns : cut[i]>0 && p.ID_PALLET==i.ID_PALLET};

execute FillDuals {
  for(var i in barcodes) {
     fillDuals.add(i,ctFill[i].dual);
     surplusVar.add(i,surplus[i]);
  }
  contentsFinal;
  Tareas;
}