/*********************************************
 * OPL 12.8.0.0 Model
 * Author: jwood
 * Creation Date: Nov 7, 2018 at 4:35:49 PM
 *********************************************/
include "order_info.mod";
include "parameters.mod";

//model to determine the maximum amount of weight and volume that can be loaded on a pallet 
//all CB that are fed are assumed to be feasible

execute {
	cplex.tilim = 30;
	cplex.parallelmode = -1;
}



dvar boolean fullPasillo[navePasillos];
dvar boolean isUsed[cbSispes];

dvar int+ use[cbs in cbSispes] in 0..demanda[cbs];


dvar float+ unusedWeight in 0..parameters["maxWeight"];
dvar float+ unusedVolume in 0..parameters["maxVolume"];
dvar float+ palletDistance;
dvar float+ maxXPallet;
dvar float+ maxYPallet;
dvar float+ minXPallet;
dvar float+ minYPallet;

dexpr float unusedWeightPenalty = parameters["unusedWeightPenalty"] * unusedWeight;
dexpr float unusedVolumePenalty = parameters["unusedVolumePenalty"] * unusedVolume;
dexpr float fullPasilloBonus = parameters["fullPasilloBonus"] * sum(np in navePasillos) fullPasillo[np];
dexpr float distancePenalty = parameters["distancePenalty"] *  palletDistance;

minimize
	unusedWeightPenalty
	+ unusedVolumePenalty
	- fullPasilloBonus
	+ distancePenalty;
	
	
subject to {
	//set the unused weight
	unusedWeight == parameters["maxWeight"] - sum(<cb,s> in cbSispes) peso[cb] * use[<cb,s>];
	
	//set the unused volume
	unusedVolume == parameters["maxVolume"] - sum(<cb,s> in cbSispes) volumen[cb] * use[<cb,s>];
	
	//if all the the quantity for a pasillo is used, then the pasillo is used
	forall(<n,p> in navePasillos)
		pasilloQty[<n,p>] * fullPasillo[<n,p>] <= sum(<cb,s> in cbSispes: nave[cb] == n && pasillo[cb] == p) use[<cb,s>];
		
	//determine if a CB is used
	forall (<cb,s> in cbSispes)
		demanda[<cb,s>] * isUsed[<cb,s>] >= use[<cb,s>];
		
	//for each lego, determine the min and max x and y
	forall (<cb,s> in cbSispes){
		maxXPallet >= x[cb] * isUsed[<cb,s>];
		maxYPallet >= y[cb] * isUsed[<cb,s>];
		minXPallet <= x[cb] * isUsed[<cb,s>] + maxX[nave[cb]] * (1 - isUsed[<cb,s>]);
		minYPallet <= y[cb] * isUsed[<cb,s>] + maxY[nave[cb]] * (1 - isUsed[<cb,s>]);
	}
		
	//detemine the distance of lego items
	palletDistance == maxXPallet - minXPallet + maxYPallet - minYPallet;
}

/*
tuple scoreType {
	float score;
}
{scoreType} score = {};
execute {score.add(unusedWeightPenalty + unusedVolumePenalty - fullPasilloBonus); }
*/

tuple useType {
	string CB;
	int SISPE;
	int ASIGNADO;
}
{useType} legoAllocation = {};
execute {
	for (var cbs in cbSispes){
		if(use[cbs] > 0) {
			legoAllocation.add(cbs.cb,cbs.sispe,use[cbs]);
		}
	}
}
