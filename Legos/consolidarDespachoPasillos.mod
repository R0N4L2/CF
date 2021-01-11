/*********************************************
 * OPL 12.8.0.0 Model
 * Author: jwood
 * Creation Date: Jan 15, 2019 at 6:11:31 PM
 *********************************************/
//model to consolidate every run through a pasillo into legos and pallets. The objective is to create fewer legos and pallets and also reduce the distance 
//traveled within a lego
 
include "parameters.mod";

tuple pasilloRunType {
	int index;
	int nave;
	int pasillo;
	string contaminante;
	float peso;
	float volumen;
	int resistencia;
	float x_min;
	float x_max;
	float y_min;
	float y_max;
}
{pasilloRunType} legoPasillos = ...;
float totalWeight = sum(lp in legoPasillos) lp.peso;
//execute {writeln(totalWeight);}

{int} naves = {lp.nave | lp in legoPasillos};
float maxX[n in naves] = max(lp in legoPasillos: lp.nave == n) lp.x_max;
float maxY[n in naves] = max(lp in legoPasillos: lp.nave == n) lp.y_max;

//{int} indexes = {lp.index | lp in legoPasillos};

tuple navePasilloType{
	int nave;
	int pasillo;
}
{navePasilloType} navePasillos = {<lp.nave,lp.pasillo> | lp in legoPasillos};
int resistencia[navePasillos] = [<lp.nave,lp.pasillo>: lp.resistencia | lp in legoPasillos];

tuple tareaNavePasilloContaminanteType{
	int tarea_index;
	int nave;
	int pasillo;
	string contaminante;
}
{tareaNavePasilloContaminanteType} tareaNavePasilloContaminantes = {<lp.index,lp.nave,lp.pasillo,lp.contaminante> | lp in legoPasillos};
float peso[tareaNavePasilloContaminantes] = [<lp.index,lp.nave,lp.pasillo,lp.contaminante>: lp.peso | lp in legoPasillos];
float volumen[tareaNavePasilloContaminantes] = [<lp.index,lp.nave,lp.pasillo,lp.contaminante>: lp.volumen | lp in legoPasillos];
float x_min[tareaNavePasilloContaminantes] = [<lp.index,lp.nave,lp.pasillo,lp.contaminante>: lp.x_min | lp in legoPasillos];
float x_max[tareaNavePasilloContaminantes] = [<lp.index,lp.nave,lp.pasillo,lp.contaminante>: lp.x_max | lp in legoPasillos];
float y_min[tareaNavePasilloContaminantes] = [<lp.index,lp.nave,lp.pasillo,lp.contaminante>: lp.y_min | lp in legoPasillos];
float y_max[tareaNavePasilloContaminantes] = [<lp.index,lp.nave,lp.pasillo,lp.contaminante>: lp.y_max | lp in legoPasillos];

tuple resistenciaDataType{
	int resistencia;
	float maxPeso;
	float maxVolumen;
	float maxPesoEncima;
}

{resistenciaDataType} resistenciaData = ...;

{int} resistencias = {rd.resistencia | rd in resistenciaData};
int maxResistencia = max(r in resistencias) r;
float maxPeso[resistencias] = [rd.resistencia: rd.maxPeso | rd in resistenciaData];
float maxVolumen[resistencias] = [rd.resistencia: rd.maxVolumen | rd in resistenciaData];
float maxPesoEncima[resistencias] = [rd.resistencia: rd.maxPesoEncima | rd in resistenciaData];
//int resistenciaSum = sum(r in resistencias) r;
int maxItems[r in resistencias] = card({lp | lp in legoPasillos: lp.resistencia == r});

int maxNave = max(lp in legoPasillos) lp.nave;

range palletIDs = 1..ftoi(parameters["maxPallets"]);


execute {
	cplex.tilim = 20 + 2 * parameters["maxPallets"];
	
	cplex.parallelmode = -1;
}

dvar boolean usePallet[palletIDs];
dvar boolean useLego[palletIDs][naves];
dvar boolean assignTNPCToPallet[tareaNavePasilloContaminantes][palletIDs];
//dvar boolean dontAssign[tareaNavePasilloContaminantes];
dvar boolean contieneContaminantes[palletIDs];

dvar float palletVolume[palletIDs] in 0..parameters["targetLoadVolume"];
dvar float palletWeight[palletIDs] in 0..parameters["targetLoadWeight"];
//dvar float legoVolume[palletIDs][naves] in 0..parameters["targetLoadVolume"];
//dvar float legoWeight[palletIDs][naves] in 0..parameters["targetLoadWeight"];
//dvar float legoResistenciaWeight[palletIDs][naves][r in resistencias] in 0..maxPeso[r];
//dvar float+ maxXLego[palletIDs][naves];
//dvar float+ maxYLego[palletIDs][naves];
//dvar float+ minXLego[palletIDs][naves];
//dvar float+ minYLego[palletIDs][naves];
//dvar float+ legoDistance[palletIDs][naves];

dexpr float palletPenalty = sum(palletID in palletIDs) usePallet[palletID];
//dexpr float missingTMPC = sum(tmpc in tareaNavePasilloContaminantes) dontAssign[tmpc];
dexpr float legoPenalty = sum(palletID in palletIDs, nave in naves) useLego[palletID][nave];
//dexpr float distancePenalty = sum(palletID in palletIDs, nave in naves) legoDistance[palletID][nave];

minimize 
	parameters["costPerPallet"] * palletPenalty
	//+ 0 * parameters["costPerPallet"] * missingTMPC
	+ parameters["costPerLego"] * legoPenalty;
	//+ parameters["distancePenalty"] * distancePenalty;

subject to {
	//determine if a contaminante is assigned to a pallet
	forall(palletID in palletIDs)
		ContCont:contieneContaminantes[palletID] * parameters["targetLoadVolume"] >= sum(tnpc in tareaNavePasilloContaminantes: tnpc.contaminante == "CONTAMINANTE") assignTNPCToPallet[tnpc][palletID] * volumen[tnpc];
		
	//if a pallet contains contaminantes, then it may not contain contaminables
	forall(palletID in palletIDs)
		contContaminable:(1 - contieneContaminantes[palletID]) * parameters["targetLoadVolume"] >= sum(tnpc in tareaNavePasilloContaminantes: tnpc.contaminante == "CONTAMINABLE") assignTNPCToPallet[tnpc][palletID] * volumen[tnpc];
	
	//every tnpc must be assigned to a pallet
	forall (tnpc in tareaNavePasilloContaminantes)
		mustAssign:sum(palletID in palletIDs) assignTNPCToPallet[tnpc][palletID] == 1; // - dontAssign[tnpc];
		
	//cycle breaking
	forall (palletID1 in palletIDs, palletID2 in palletIDs: palletID1 == palletID2 - 1){
		cycleBreak:usePallet[palletID1] >= usePallet[palletID2];
	}		
		
	//cannot assign to a pallet that is not used
	forall (tnpc in tareaNavePasilloContaminantes, palletID in palletIDs)
		c_useTNPC_UsePallet:assignTNPCToPallet[tnpc][palletID] <= usePallet[palletID];
	forall (nave in naves, palletID in palletIDs)
		c_useLegoUsePallet:useLego[palletID][nave] <= usePallet[palletID];

	//cannot have more legos per pallet than the limit
	forall (palletID in palletIDs)
		maxLegos:sum(nave in naves) useLego[palletID][nave] <= parameters["maxLegos"];
		
	//if an tnpc is assigned to a tarea, the lego must be used
	forall (tnpc in tareaNavePasilloContaminantes, palletID in palletIDs)
		tnpcUseLego:assignTNPCToPallet[tnpc][palletID] <= useLego[palletID][tnpc.nave];
		
	//each pallet must respect the limits for the resistencia volume and weight;
	forall (palletID in palletIDs, r in resistencias){
		resW:sum(<t,n,p,c> in tareaNavePasilloContaminantes: resistencia[<n,p>] == r) peso[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] <= maxPeso[r];
		resV:sum(<t,n,p,c> in tareaNavePasilloContaminantes: resistencia[<n,p>] == r) volumen[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] <= maxVolumen[r];
	}
	
	//calculate pallet volume and pallet weight
	forall (palletID in palletIDs){
		palletW:sum(<t,n,p,c> in tareaNavePasilloContaminantes) peso[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] == palletWeight[palletID];
		palletV:sum(<t,n,p,c> in tareaNavePasilloContaminantes) volumen[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] == palletVolume[palletID];
	}
	
	//each pallet has a max weight and volume
	forall (palletID in palletIDs){
		maxW:sum(<t,n,p,c> in tareaNavePasilloContaminantes) peso[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] <= parameters["targetLoadWeight"];
		maxV:sum(<t,n,p,c> in tareaNavePasilloContaminantes) volumen[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] <= parameters["targetLoadVolume"];
	}
	
	//for each lego, determine the min and max x and y
//	forall (<t,n,p,c> in tareaNavePasilloContaminantes, palletID in palletIDs){
//		maxXLego[palletID][n] >= x_max[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID];
//		maxYLego[palletID][n] >= y_max[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID];
//		minXLego[palletID][n] <= x_min[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] + maxX[n] * (1 - assignTNPCToPallet[<t,n,p,c>][palletID]);
//		minYLego[palletID][n] <= y_min[<t,n,p,c>] * assignTNPCToPallet[<t,n,p,c>][palletID] + maxY[n] * (1 - assignTNPCToPallet[<t,n,p,c>][palletID]);
//	}
//		
//	//detemine the distance of lego items
//	forall (palletID in palletIDs, n in naves)
//	  	legoDistance[palletID][n] == maxXLego[palletID][n] - minXLego[palletID][n] + maxYLego[palletID][n] - minYLego[palletID][n];
}


tuple newAssignmentType{
	int pallet_index;
	int nave;
	int pasillo;
	int tarea_index;
	string contaminante;
}
{newAssignmentType} newAssignments = {<palletID,n,p,t,c> | <t,n,p,c> in tareaNavePasilloContaminantes, palletID in palletIDs: assignTNPCToPallet[<t,n,p,c>][palletID] >= 0.99};
//execute {writeln(newAssignments);}

