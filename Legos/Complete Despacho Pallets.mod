/*********************************************
 * OPL 12.8.0.0 Model
 * Author: jwood
 * Creation Date: Nov 7, 2018 at 4:35:49 PM
 *********************************************/
include "despacho_info.mod";
include "parameters.mod";

//model to determine the maximum amount of weight and volume that can be loaded on a pallet 
//all CB that are fed are assumed to be feasible

execute {
	cplex.tilim = 30;
	cplex.parallelmode = -1;
}


dvar boolean fullPasillo[pasillos];
dvar boolean isUsed[cbs];
dvar boolean contieneContaminantes;

dvar int+ use[cb in cbs] in 0..demanda[cb];

dvar float+ unusedWeight in 0..parameters["maxWeight"];
dvar float+ unusedVolume in 0..parameters["maxVolume"];
dvar float+ palletDistance;
dvar float+ maxXPallet;
dvar float+ maxYPallet;
dvar float+ minXPallet;
dvar float+ minYPallet;

dexpr float unusedWeightPenalty = unusedWeight;
dexpr float unusedVolumePenalty = unusedVolume;
dexpr float fullPasilloBonus = sum(p in pasillos) fullPasillo[p];
dexpr float distancePenalty = palletDistance;

minimize
	parameters["unusedWeightPenalty"] * unusedWeightPenalty
	+ parameters["unusedVolumePenalty"] * unusedVolumePenalty
	- parameters["fullPasilloBonus"] * fullPasilloBonus
	+ parameters["distancePenalty"] * distancePenalty;
		
subject to {
	//determine if a contaminante is assigned to a pallet
	contieneContaminantes * parameters["targetLoadVolume"] >= sum(cb in cbs: categoriaCont[cb] == "CONTAMINANTE") use[cb] * volumen[cb];
	
	//if a pallet contains contaminantes, it may not contain contaminables
	(1 - contieneContaminantes) * parameters["targetLoadVolume"] >= sum(cb in cbs: categoriaCont[cb] == "CONTAMINABLE") use[cb] * volumen[cb];
	
	//set the unused weight
	unusedWeight == parameters["maxWeight"] - sum(cb in cbs) peso[cb] * use[cb];
	
	//set the unused volume
	unusedVolume == parameters["maxVolume"] - sum(cb in cbs) volumen[cb] * use[cb];
	
	//if all the the quantity for a pasillo is used, then the pasillo is used
	forall(p in pasillos)
		pasilloQty[p] * fullPasillo[p] <= sum(cb in cbs: pasillo[cb] == p) use[cb];
		
	//determine if a CB is used
	forall (cb in cbs)
		demanda[cb] * isUsed[cb] >= use[cb];
		
	//for each lego, determine the min and max x and y
	forall (cb in cbs){
		maxXPallet >= x[cb] * isUsed[cb];
		maxYPallet >= y[cb] * isUsed[cb];
		minXPallet <= x[cb] * isUsed[cb] + maxX * (1 - isUsed[cb]);
		minYPallet <= y[cb] * isUsed[cb] + maxY * (1 - isUsed[cb]);
	}
		
	//detemine the distance of lego items
	palletDistance == maxXPallet - minXPallet + maxYPallet - minYPallet;

}


tuple useType {
	string CB;
	int ASIGNADO;
	string CONTAMINANTE;
}
{useType} legoAllocation = {};
execute {
	for (var cb in cbs){
		if(use[cb] > 0) {
			legoAllocation.add(cb, use[cb], categoriaCont[cb]);
		}
	}
}
