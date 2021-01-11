/*********************************************
 * OPL 12.8.0.0 Model
 * Author: jwood
 * Creation Date: Nov 8, 2018 at 7:28:47 PM
 *********************************************/

include "despacho_info.mod";
include "parameters.mod";
include "resistencia.mod";
 
//choose which legos to assign to which pallets so as to minimize the maximum 

{int} resistenciasDI = {di.resistencia | di in despachoInfo};
float maxPalletsPeso[r in resistenciasDI] 
	= (1 / maxPeso[r]) * sum(di in despachoInfo: di.resistencia == r) di.peso * di.demanda;
float maxPalletsVolumen[r in resistenciasDI] 
	= (1 / maxVolumen[r]) * sum(di in despachoInfo: di.resistencia == r) di.volumen * di.demanda;

tuple legoInfoType{
	int lidx;
	string codigodespacho;
	int resistance;
	int pidx;
	float volumen;
	float peso;
}
{legoInfoType} legoInfo = ...;

{int} resistenciaLegos[r in resistenciasDI] = {li.lidx | li in legoInfo: li.resistance == r};
{int} legoIDs = {li.lidx | li in legoInfo};
float legoPeso[legoIDs] = [li.lidx : li.peso | li in legoInfo];
float legoVolumen[legoIDs] = [li.lidx : li.volumen | li in legoInfo];
{int} palletIDs = {li.pidx | li in legoInfo};

tuple legoContentType{
	int lidx;
	string cb;
	int asignado;
}
{legoContentType} legoContents = ...;

execute {
	cplex.tilim = 30;
	cplex.parallelmode = -1;
}

dvar boolean isUsed[legoIDs];


dvar float+ palletsLeft;
dvar float+ palletsLeftPeso[r in resistenciasDI] in 0..maxPalletsPeso[r];
dvar float+ palletsLeftVolumen[r in resistenciasDI] in 0..maxPalletsVolumen[r];

minimize
	palletsLeft;
	
subject to {

	//the max pallets is greater than or equal to the pallets at each resistance level and for weight and volume
	forall (r in resistenciasDI){
		palletsLeft >= palletsLeftPeso[r];
		palletsLeft >= palletsLeftVolumen[r];
	}		
	
	//determine the number of pallets left based on the legos chosen
	forall (r in resistenciasDI){
		palletsLeftPeso[r] == maxPalletsPeso[r] - sum(lidx in legoIDs: lidx in resistenciaLegos[r]) legoPeso[lidx] * isUsed[lidx] / maxPeso[r];
		palletsLeftVolumen[r] == maxPalletsVolumen[r] - sum(lidx in legoIDs: lidx in resistenciaLegos[r]) legoVolumen[lidx] * isUsed[lidx] / maxVolumen[r];
	}
		
	//no more than one (additional) legos can be assigned per pallet. 
	//TODO: increase to maxLegos - 1 and add constraint to keep the base pallet and additional legos all compliant with the same resistencia category.
	forall (pidx in palletIDs)
		sum(li in legoInfo: li.pidx == pidx) isUsed[li.lidx] <= 1;
		
	//limit the use of legos based upon demand of each cb-sispe
	forall (cb in cbs)
		sum(<lidx,cb,asignado> in legoContents) asignado * isUsed[lidx] <= demanda[cb];
}

tuple usedLegoType{
	int lidx;
}
{usedLegoType} usedLegos = {<lidx> | lidx in legoIDs: isUsed[lidx] > 0.99};
//execute{ writeln(usedLegos);}