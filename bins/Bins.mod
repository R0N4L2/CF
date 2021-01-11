/*********************************************
 * OPL 12.7.1.0 Model
 * Author: jwood
 * Creation Date: Jul 3, 2018 at 11:18:00 AM
 *********************************************/
 
//This is meant to run for the cold items per locale. Only items that are compatible may be in the same bin, so this should run
//just for compatible items that require a bin.

{string} binTypes = ...;
int binsDisponibles[binTypes] = ...;
float binVolume[binTypes] = ...;
float binCost[binTypes] = ...;

float missedShipmentPenalty = ...;
float bodegaPenalty = ...;

//TODO: given that entering pasillo 1 means returning in pasillo 2, use some pre-processing to unite pasillos.
tuple productInformationType {
	string product;
	int bodega;
	float weight;
	float volume;
	int demand;
}
{productInformationType} productInformation = ...;
{string} products = {pi.product | pi in productInformation};
int maxPossibleBodega = max(pi in productInformation) pi.bodega;
float totalVolume = sum(pi in productInformation) pi.volume * pi.demand;

int maxBinsPossible[b in binTypes] = 0;
execute{
	//the number of possible bins depends on the number of available bins and the demand for the bins based on product demand
	for (var binType in binTypes){
		maxBinsPossible[binType] = Math.min(binsDisponibles[binType],(1 + Math.floor(totalVolume / binVolume[binType])));
	}
}

tuple binTypeBinNumberType{
	string binType;
	int binNumber;
}
{binTypeBinNumberType} binTypeNumbers = {<binType,binNumber> | binType in binTypes, binNumber in 1..maxBinsPossible[binType]};

execute{
	cplex.tilim = 120;
	cplex.parallelmode = -1;
	cplex.heurfreq = 1;
}


//Begin
//Variables
dvar boolean useBin[binTypeNumbers];
dvar float+ binVolumeSent[btn in binTypeNumbers] in 0..binVolume[btn.binType];
dvar int+ assignProductToBin[products][binTypeNumbers];
dvar boolean productIsAssignedToBin[products][binTypeNumbers];
dvar float+ maxBodega[binTypeNumbers] in 0..maxPossibleBodega;
dvar float+ minBodega[binTypeNumbers] in 0..maxPossibleBodega;

dvar float+ volumeNotShipped;

dexpr float shipmentCost = sum(btn in binTypeNumbers) binCost[btn.binType] * useBin[btn];
dexpr float missedShipmentCost = missedShipmentPenalty * volumeNotShipped; 
dexpr float bodegaDist = bodegaPenalty * sum(btn in binTypeNumbers) (maxBodega[btn] - minBodega[btn]);

//Objective
minimize
	shipmentCost + missedShipmentCost +bodegaDist;
	
//Constraints
subject to {
	//the volume shipped + the volume not shipped equals the total volume;
	sum(btn in binTypeNumbers) 
		binVolumeSent[btn] + volumeNotShipped == totalVolume;
	
	//calculate the volume shipped for each bintype and number
	forall (btn in binTypeNumbers)
		sum(pi in productInformation)
			pi.volume * assignProductToBin[pi.product][btn] == binVolumeSent[btn];
		
	//ensure the amount shipped of each item is less than or equal to the demand
	forall(pi in productInformation)
		sum(btn in binTypeNumbers)
			assignProductToBin[pi.product][btn] <= pi.demand;
		
	//a bin may only have volume if it is used
	forall(btn in binTypeNumbers)
		binVolumeSent[btn] <= binVolume[btn.binType] * useBin[btn];
	
	//determine if a product is assigned	
	forall(btn in binTypeNumbers, pi in productInformation){
		assignProductToBin[pi.product][btn] <= pi.demand * productIsAssignedToBin[pi.product][btn];
	}
	
	//set the min and max pasillo values to 0 if a bin is not used	
	forall(btn in binTypeNumbers){
		maxBodega[btn] <= maxPossibleBodega * useBin[btn];
		minBodega[btn] <= maxPossibleBodega * useBin[btn];
		minBodega[btn] <= maxBodega[btn];
	}
	
	//the max pasillo is the largest value for pasillo of all the pasillos that the bin number visits
	forall(btn in binTypeNumbers, pi in productInformation){
		maxBodega[btn] >= pi.bodega * productIsAssignedToBin[pi.product][btn];
	//the min pasillo is the minimum value for pasillo of all the pasillo that the bin number visits
		minBodega[btn] <= maxPossibleBodega * (1 - productIsAssignedToBin[pi.product][btn]) + pi.bodega * productIsAssignedToBin[pi.product][btn];
	}	

	//cycle-breaking constraints
	forall(btn in binTypeNumbers: btn.binNumber > 1)
		useBin[<btn.binType,btn.binNumber-1>] >= useBin[btn];
}
//End

tuple productBinTypeNumberQtyType{
	string product;
	string binType;
	int binNumber;
	int quantity;
}
{productBinTypeNumberQtyType} productBinTypeNumberQty = {<pi.product,btn.binType,btn.binNumber,assignProductToBin[pi.product][btn]> | btn in binTypeNumbers, pi in productInformation: assignProductToBin[pi.product][btn] >= 0.9};
execute{writeln(productBinTypeNumberQty);}