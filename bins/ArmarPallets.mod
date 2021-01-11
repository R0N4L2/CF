/*********************************************
 * OPL 12.8.0.0 Model
 * Author: lilipili
 * Creation Date: 11/7/2018 at 8:31:44
 *********************************************/

//Tuples
tuple content{
	int id;
	int barCode;
	float quantity;
}

tuple subpallet{
	int id;
	float weight;
	float volume;
	float height;
	string contamination;
	int resistence;
	float minX;
	float minY;
	float maxX;
	float maxY;
}
{subpallet} subpallets = ...;

tuple pallet{
	int id;
	float weight;
	float volume;
}

tuple barCode{
	int barCode;
	float demand;
}

tuple resistencia{
	int idResistencia;
	float weightMaxAbove;
	float weightMax;
}



//Sets


int numSubpallets = card(subpallets);

{content} contents = ...;
int numPallets = ...;
range pallets=1..numPallets;
{barCode} barCodes = ...;
{resistencia} grupoResistencia = ...;

//Contaminants sets
//{int} contaminables = ...;
//{int} contaminantes = ...;

//Parameters
float weightMax = ...;
float heightMax[pallets] = ...;
float volumeMax = ...;
float demandTot = ...;
float maxPossibleDistanceX = max(i in subpallets) i.maxX;
float maxPossibleDistanceY = max(i in subpallets) i.maxY;

//Decision variables
//assign subpallets to pallets
dvar boolean assignation[subpallets][pallets];
//assign pallet to task
dvar boolean usedPallet[pallets];
//determine the demand sent in each pallet
dvar float+ sentBarCode[barCodes][pallets];
//maximum X distance between products
dvar float+ maxDistanceX[pallets];
//maximum Y distance between products
dvar float+ maxDistanceY[pallets];
//minimum X distance between products
dvar float+ minDistanceX[pallets];
//minimum Y distance between products
dvar float+ minDistanceY[pallets];
//weightAbove
dvar float+ weightAbove[1..numPallets];
dvar float+ missingBarCode[k in barCodes] in 0..k.demand;

//FO 
dexpr float objNumPallets = sum(i in pallets)usedPallet[i];
dexpr float objDistance = sum(i in pallets)((maxDistanceX[i]-minDistanceX[i])+(maxDistanceY[i]-minDistanceY[i]));
dexpr float missingDemandPenalty  = 1000 * sum(k in barCodes) missingBarCode[k];
minimize
  50*objNumPallets 
  + 0.01*objDistance 
  + missingDemandPenalty;

//Constraints
subject to{

//Assignation constraint
forall(i in subpallets, j in pallets)
  assignation[i][j]<=usedPallet[j];
 
//a subpallet may only be assigned to at most one pallet 
forall(i in subpallets)
  sum(j in pallets)assignation[i][j]<=1;

//Demand constraints
//Define total quantity sent per bar code per pallet
forall(j in pallets, k in barCodes)
  sum(i in subpallets, c in contents : c.id==i.id && c.barCode==k.barCode)
    (assignation[i][j]*c.quantity) == sentBarCode[k][j];

//forall(j in pallets, k in barCodes)
//  sentBarCode[k][j]<=usedPallet[j]*weightMax;

//Quantity sent should be equal to the demand
forall(k in barCodes)
  sum(j in pallets)sentBarCode[k][j] + missingBarCode[k] == k.demand;

//Weight constraints
//Maximum weight allowed in a pallet should be respected
forall(j in pallets)
  sum(i in subpallets)(assignation[i][j]*i.weight)<=weightMax*usedPallet[j];

//max volume per pallet constraint
forall(j in pallets)
  sum(i in subpallets)(assignation[i][j]*i.volume)<=volumeMax*usedPallet[j];

//Contaminants constraints
forall(j in pallets, a in subpallets, b in subpallets: a.contamination=="A" && b.contamination=="B")
  assignation[a][j]+assignation[b][j]<=1;

//Resistence constraints
forall(g in grupoResistencia, j in pallets)
  sum(i in subpallets: i.resistence>g.idResistencia) assignation[i][j]*i.weight<=g.weightMaxAbove;

forall(g in grupoResistencia, j in pallets)
  sum(i in subpallets:i.resistence>=g.idResistencia) assignation[i][j]*i.weight<=g.weightMax;


//set maxX and maxY to zero when the pallt is not used
forall(j in pallets){
	maxDistanceX[j] <= maxPossibleDistanceX * usedPallet[j];
	maxDistanceY[j] <= maxPossibleDistanceY * usedPallet[j];
	minDistanceX[j] <= maxPossibleDistanceX * usedPallet[j];
	minDistanceY[j] <= maxPossibleDistanceY * usedPallet[j];
}

//the max distance is the largest value for x distance of all the distances that the pallet number visits
forall(j in pallets, i in subpallets)
	maxDistanceX[j] >= i.maxX * assignation[i][j];
	
//the max distance is the largest value for x distance of all the distances that the pallet number visits
forall(j in pallets, i in subpallets)
	maxDistanceY[j] >= i.maxY * assignation[i][j];
	
//the min distance is the shortest value for x distance of all the distances that the pallet number visits
forall(j in pallets, i in subpallets)
	minDistanceX[j] <= maxPossibleDistanceX * (1 - assignation[i][j]) 
						+ i.maxX * assignation[i][j];
						
//the min distance is the shortest value for x distance of all the distances that the pallet number visits
forall(j in pallets, i in subpallets)
	minDistanceY[j] <= maxPossibleDistanceY * (1 - assignation[i][j]) 
						+ i.maxY * assignation[i][j];

//cycle-breaking constraints
forall(i in pallets: i > 1)
	usedPallet[i-1] >= usedPallet[i];
  
}


//{pallet} palletInfo= {<id,weight,volume> | id in pallets : usedPallet[id]==1};

 


execute RESULTS{
	for(var j in pallets){
		if(usedPallet[j]==1){
			writeln("Los subpallets asignados al pallet " + j + " son:")
			for(var i in subpallets){
				if(assignation[i][j]>0){
					writeln("Subpallet " + i.id)
				}	
			}
		}					
	}			

}
