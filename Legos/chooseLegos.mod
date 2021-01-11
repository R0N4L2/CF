/*********************************************
 * OPL 12.8.0.0 Model
 * Author: jwood
 * Creation Date: Oct 26, 2018 at 1:53:36 PM
 *********************************************/
include "order_info.mod";
include "parameters.mod";
include "resistencia.mod";

tuple palletSpaceType {
	int pidx;
	float weightRemaining; //needs to be the weight that an go at or above the resistance level
	float volumeRemaining;
	int contaminante; //-1 if not set
	int minResistencia;
	int sispe;
}
{palletSpaceType} palletSpace = ...;
{int} palletIDs = {ps.pidx | ps in palletSpace};

tuple legoType {
	key int lidx;
	//float weightRemaining;
	//float volumeRemaining;
	float peso;
	float volumen;
	int esBase;
	int contaminante; //must be 0 or 1
	int assignedPallet; //if assigned, it is mandatory, not assigned is 0
	int sispe;
}
{legoType} legos = ...;
{int} legoIDs = {lego.lidx | lego in legos: lego.assignedPallet == 0};
{int} palletsWithBaseAssigned = {lego.assignedPallet | lego in legos: lego.assignedPallet > 0};
{int} palletsWithoutBaseAssigned = palletIDs diff palletsWithBaseAssigned;

tuple legoContentType {
	key int lidx;
	key string cb;
	key int sispe;
	int cantidad;
}
{legoContentType} legoContent = ...;

tuple legoPalletType {
	int lidx;
	int pidx;
}
//{legoPalletType} legosToExistingPallets = {
//	<lego.lidx,pallet.pidx> | lego in legos, pallet in palletSpace:
//	pallet.
//};

{legoPalletType} legoPallets = {<lego.lidx,pallet.pidx> | lego in legos, pallet in palletSpace:
	lego.peso <= pallet.weightRemaining 
	&& lego.volumen <= pallet.volumeRemaining
	&& lego.assignedPallet == 0 //only non-assigned pallets 
	&& (lego.esBase == 0 || (lego.esBase == 1 && pallet.pidx not in palletsWithBaseAssigned))
	&& (pallet.contaminante == -1 || (pallet.contaminante == lego.contaminante))
	&& (pallet.sispe == -1 || pallet.sispe == lego.sispe)
}; 
//{legoPalletType} legoPallets = {};
int netDemand[<cb,s> in cbSispes] = demanda[<cb,s>] - sum(lego in legos, lc in legoContent: 
	lego.assignedPallet > 0 && lego.lidx == lc.lidx && lc.cb == cb && lc.sispe == s) lc.cantidad;
{string} cbSinSispe = {cb | <cb,s> in cbSispes: s == 0};
{string} cbConSispe = {cb | <cb,s> in cbSispes: s == 1};

dvar boolean usePallet[palletIDs];
dvar boolean useLego[legoIDs];
dvar boolean assignLegoToPallet[legoPallets];
dvar boolean esContaminante[palletsWithoutBaseAssigned];
dvar boolean esSispe[palletsWithoutBaseAssigned];

dvar float+ unmetDemand[<cb,s> in cbSispes] in 0..demanda[<cb,s>];
 
dexpr float numPallets = parameters["costPerPallet"] * sum(pidx in palletIDs) usePallet[pidx];
dexpr float legosUsed = parameters["costPerLego"] * sum(lidx in legoIDs) useLego[lidx];
dexpr float unmetDemandPenalty = 10000 * sum(cbs in cbSispes) unmetDemand[cbs];
minimize 
	numPallets
	+ legosUsed
	+ unmetDemandPenalty;
	
subject to {
	// a pallet is used when the any lego is assigned to it.
	forall (pidx in palletIDs) 
		parameters["maxLegosPerPallet"] * usePallet[pidx] >= sum(<lidx,pidx> in legoPallets) assignLegoToPallet[<lidx,pidx>];
		
	//is a lego is already assigned, the pallet gets used
	forall (lego in legos: lego.assignedPallet > 0)
		usePallet[lego.assignedPallet] == 1;
		
	//if a pallet is used, so is the previous one
	forall (pidx1 in palletIDs, pidx2 in palletIDs: ord(palletIDs,pidx1) ==  ord(palletIDs,pidx2) - 1)
		usePallet[pidx1] >= usePallet[pidx2];
		
	//the number of legos in a pallet must be at or below the maximum number of legos
	forall (pidx in palletIDs)
		sum(<lidx,pidx> in legoPallets) assignLegoToPallet[<lidx,pidx>] + sum(lego in legos: lego.assignedPallet == pidx ) 1 
		<= parameters["maxLegosPerPallet"];
		
	//only one base may be added per pallet
	forall (pidx in palletIDs: pidx not in palletsWithBaseAssigned)
		c_base: sum(<lidx,pidx> in legoPallets, lego in legos: lego.lidx == lidx && lego.esBase == 1) assignLegoToPallet[<lidx,pidx>] <= 1;
		
	//meet the demand of all CBs
	//forall (<cb,s> in cbSispes)
	forall(cb in cbSinSispe)
		c_demandaSinSispe: sum(lego in legos, lc in legoContent: lego.assignedPallet == 0 && lego.lidx == lc.lidx && lc.cb == cb) useLego[lego.lidx] * lc.cantidad
			>= netDemand[<cb,0>] - unmetDemand[<cb,0>];
	forall(cb in cbConSispe)
		c_demandaConSispe: sum(lego in legos, lc in legoContent: lego.assignedPallet == 0 && lego.lidx == lc.lidx && lc.cb == cb) useLego[lego.lidx] * lc.cantidad
			>= netDemand[<cb,1>] - unmetDemand[<cb,1>];

	//assignLegoToPallet[<9,6>] == 1;
		
			
	//a lego is used if there is an assignement
	forall (<lidx,pidx> in legoPallets)
		assignLegoToPallet[<lidx,pidx>] <= useLego[lidx];
		
	//limit the total weight and volume on each pallet with assigned base
	forall(pidx in palletsWithBaseAssigned){
		c_assignedPalletWeight: sum(<lidx,pidx> in legoPallets, lego in legos: lego.lidx == lidx) assignLegoToPallet[<lidx,pidx>] * lego.peso 
		<= sum(pallet in palletSpace: pallet.pidx == pidx) pallet.weightRemaining;
		c_assignedPalletVolume: sum(<lidx,pidx> in legoPallets, lego in legos: lego.lidx == lidx) assignLegoToPallet[<lidx,pidx>] * lego.volumen 
		<= sum(pallet in palletSpace: pallet.pidx == pidx) pallet.volumeRemaining; 	 	
	}
	//limit the weight and volume of the other pallets
	forall(pidx in palletIDs, r in resistencias: pidx not in palletsWithBaseAssigned){
		c_palletWeight: sum(<lidx,pidx> in legoPallets, lc in legoContent: lc.lidx == lidx && resistencia[lc.cb] == r) 
			assignLegoToPallet[<lidx,pidx>] * peso[lc.cb] * lc.cantidad 
		<= maxPeso[r];
		c_palletVolume: sum(<lidx,pidx> in legoPallets, lc in legoContent: lc.lidx == lidx && resistencia[lc.cb] == r) 
			assignLegoToPallet[<lidx,pidx>] * volumen[lc.cb] * lc.cantidad 
		<= maxVolumen[r];
	}
	
	//a lego may only be assigned once
	forall (lidx in legoIDs)
		sum(<lidx,pidx> in legoPallets) assignLegoToPallet[<lidx,pidx>] == useLego[lidx];
		
	//for pallets that do not have a specific field for contaminante, force all to be the same
	forall (<lidx,pidx> in legoPallets, lego in legos: pidx in palletsWithoutBaseAssigned && lego.lidx == lidx && lego.contaminante == 0)
		assignLegoToPallet[<lidx,pidx>] <= 1 - esContaminante[pidx];
	forall (<lidx,pidx> in legoPallets, lego in legos: pidx in palletsWithoutBaseAssigned && lego.lidx == lidx && lego.contaminante == 1)
		assignLegoToPallet[<lidx,pidx>] <= esContaminante[pidx];
		
	//for pallets that do not have a specific sispe, determine the cispe value
	forall (<lidx,pidx> in legoPallets, lego in legos: pidx in palletsWithoutBaseAssigned && lego.lidx == lidx && lego.sispe == 0)
		assignLegoToPallet[<lidx,pidx>] <=  1 - esSispe[pidx];
	forall (<lidx,pidx> in legoPallets, lego in legos: pidx in palletsWithoutBaseAssigned && lego.lidx == lidx && lego.sispe == 1)
		assignLegoToPallet[<lidx,pidx>] <=  esSispe[pidx];
}

//need which legos are chosen and which CB,S have unmet demand.
