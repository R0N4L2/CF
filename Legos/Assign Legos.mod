/*********************************************
 * OPL 12.8.0.0 Model
 * Author: jwood
 * Creation Date: Nov 8, 2018 at 7:28:47 PM
 *********************************************/

include "order_info.mod";
include "parameters.mod";
include "resistencia.mod";
 
//choose which legos to assign to which pallets so as to minimize the maximum 
tuple contaminanteSispeResistenciaType {
	int contaminante;
	int sispe;
	int resistencia;
}
{contaminanteSispeResistenciaType} contaminanteSispeResistencias = {<oi.contaminante, oi.sispe, oi.resistencia> | oi in orderInfo};
float maxPalletsPeso[<c,s,r>  in contaminanteSispeResistencias] 
	= (1 / maxPeso[r]) * sum(oi in orderInfo: oi.resistencia == r
						&& oi.sispe == s
						&& oi.contaminante == c) oi.peso * oi.demanda;
float maxPalletsVolumen[<c,s,r>  in contaminanteSispeResistencias] 
	= (1 / maxVolumen[r]) * sum(oi in orderInfo: oi.resistencia == r
						&& oi.sispe == s
						&& oi.contaminante == c) oi.volumen * oi.demanda;
tuple contaminanteSispeType {
	int contaminante;
	int sispe;
}
{contaminanteSispeType} contaminanteSispes = {<oi.contaminante, oi.sispe> | oi in orderInfo};



tuple legoInfoType{
	int lidx;
	int contaminante;
	int sispe;
	int resistance;
	int pidx;
	float volumen;
	float peso;
}
{legoInfoType} legoInfo = ...;
{int} csrLegos[<c,s,r>  in contaminanteSispeResistencias] = {li.lidx | li in legoInfo: li.contaminante == c && li.sispe == s && li.resistance == r};
{int} legoIDs = {li.lidx | li in legoInfo};
float legoPeso[legoIDs] = [li.lidx : li.peso | li in legoInfo];
float legoVolumen[legoIDs] = [li.lidx : li.volumen | li in legoInfo];
{int} palletIDs = {li.pidx | li in legoInfo};

tuple legoContentType{
	int lidx;
	string cb;
	int sispe;
	int asignado;
}
{legoContentType} legoContents = ...;

execute {
	cplex.tilim = 30;
	cplex.parallelmode = -1;
}

dvar boolean isUsed[legoIDs];

dvar float+ maxPalletsLeft[contaminanteSispes];
dvar float+ palletsLeftPeso[<c,s,r>  in contaminanteSispeResistencias] in 0..maxPalletsPeso[<c,s,r>];
dvar float+ palletsLeftVolumen[<c,s,r>  in contaminanteSispeResistencias] in 0..maxPalletsVolumen[<c,s,r>];

minimize
	sum(cs in contaminanteSispes) maxPalletsLeft[cs];
	
subject to {

	//the max pallets is greater than or equal to the pallets at each resistance level and for weight and volume
	forall (<c,s,r>  in contaminanteSispeResistencias){
		maxPalletsLeft[<c,s>] >= palletsLeftPeso[<c,s,r>];
		maxPalletsLeft[<c,s>] >= palletsLeftVolumen[<c,s,r>];
	}		
	
	//determine the number of pallets left based on the legos chosen
	forall (<c,s,r>  in contaminanteSispeResistencias){
		palletsLeftPeso[<c,s,r>] == maxPalletsPeso[<c,s,r>] - sum(lidx in legoIDs: lidx in csrLegos[<c,s,r>]) legoPeso[lidx] * isUsed[lidx] / maxPeso[r];
		palletsLeftVolumen[<c,s,r>] == maxPalletsVolumen[<c,s,r>] - sum(lidx in legoIDs: lidx in csrLegos[<c,s,r>]) legoVolumen[lidx] * isUsed[lidx] / maxVolumen[r];
	}
		
	//no more than one lego can be assigned per pallet
	forall (pidx in palletIDs)
		sum(li in legoInfo: li.pidx == pidx) isUsed[li.lidx] <= 1;
		
	//limit the use of legos based upon demand of each cb-sispe
	forall (<cb,s> in cbSispes)
		sum(<lidx,cb,s,asignado> in legoContents) asignado * isUsed[lidx] <= demanda[<cb,s>];
}

tuple usedLegoType{
	int lidx;
}
{usedLegoType} usedLegos = {<lidx> | lidx in legoIDs: isUsed[lidx] > 0.99};