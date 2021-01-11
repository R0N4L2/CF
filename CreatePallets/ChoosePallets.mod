/*********************************************
 * OPL 12.7.1.0 Model
 * Author: jwood
 * Creation Date: Aug 4, 2018 at 1:37:01 PM
 *********************************************/
float MAXVOLUME = ...;
float MAXWEIGHT = ...;
float PALLETCOST = ...;
float DISTANCECOST = ...;

{string} barcodes = ...;

int demand[barcodes] = ...;
float volume[barcodes] = ...;
float weight[barcodes] = ...;
float x[barcodes] = ...;
float y[barcodes] = ...;
string ubicacion[barcodes] = ...;
int resistance[barcodes] = ...;
string contamination[barcodes] = ...;
int nave[barcodes] = ...;

float largestX = max(b in barcodes) x[b];
float largestY = max(b in barcodes) y[b];

{int} resistances = ...;
float maxWeight[resistances] = ...;
float maxWeightAbove[resistances] = ...;

// Output dual values used to fill in the sub model.
float Duals[barcodes] = ...;

tuple  pattern {
   key int id;
   key string inBarcode;
   float quantity;
}

tuple locationXY{
	key int id;	
	float minx;
	float miny;
	float maxx;
	float maxy;
	string contamination;
}

{pattern} Patterns = ...;
{locationXY} PatternInfo = ...;
tuple patternCostType{
	int id;
	float cost;
}

{patternCostType} PatternCosts = ...;

//int numPatterns = card(patternIDs);

{int} patternIDs = {i | <i,c> in PatternCosts};
float patternItems[i in patternIDs] = sum(<i,b,q> in Patterns) 1;
float patternWeight[i in patternIDs] = sum(<i,b,q> in Patterns) q*weight[b];
float patternVolume[i in patternIDs] = sum(<i,b,q> in Patterns) q*volume[b];

//Solution
tuple finalPallets{
	int idPattern;
	int used;
	float weight;
	float volume;
}

{pattern} PatternsFinal = {};
{pattern} PatternsModif = {};

int sumaDemanda[barcodes];


tuple subpallet{
	int id;
	int used;
	float weight;
	float volume;
	string contamination;
	int resistance;
	float minx;
	float miny;
	float maxx;
	float maxy;
}

tuple content{
	int id;
	string barcode;
	float quantity;
	int location;
}

{subpallet} solutionPallets = {};
{subpallet} solutionPalletsModif = {};
{subpallet} solutionPalletsFinal = {};
{subpallet} subpallets = {};
{content} contents = {};
{content} contentsDef = {};

tuple pallet{
	int id;
	float weight;
	float volume;
	{string} listSub;
}

{string} lista = {};
{pallet} palletInfo = {};
{int} numPalletsDef = {};
{int} numPalletsNew = {};

dvar int Cut[PatternCosts] in 0..1000000;
dvar boolean isCut[PatternCosts];
dvar float+ adicional[barcodes];
dvar float+ falta[barcodes];

dvar float+ minItems;
dvar float+ maxItems;
dvar float+ minPeso;
dvar float+ maxPeso;
dvar float+ minVolumen;
dvar float+ maxVolumen;

minimize
  sum( <p,c> in PatternCosts ) (c * Cut[<p,c>]);
    /*+ 58*sum(b in barcodes) (adicional[b]+falta[b])
    + 10*(maxItems - minItems)
    + (58/500)*(maxPeso - minPeso)
    + (58/1.5)*(maxVolumen - minVolumen);*/
    
subject to {
  forall( b in barcodes ) 
   ctFill:
     sum(<p,c> in PatternCosts, <p,b,q> in Patterns) 
     	q*Cut[<p,c>] >= demand[b];// + adicional[b] - falta[b];
  /*
  forall(<p,c> in PatternCosts){
  	minItems <= Cut[<p,c>] * patternItems[p] + 100 * (1-Cut[<p,c>]);
  	maxItems >= Cut[<p,c>] * patternItems[p];  
  }

  forall(<p,c> in PatternCosts){
  	minPeso <= Cut[<p,c>] * patternWeight[p] + 1000 * (1-Cut[<p,c>]);
  	maxPeso >= Cut[<p,c>] * patternWeight[p];  
  }

  forall(<p,c> in PatternCosts){
  	minVolumen <= Cut[<p,c>] * patternWeight[p] + 1000 * (1-Cut[<p,c>]);
  	maxVolumen >= Cut[<p,c>] * patternWeight[p];  
  }
  
  forall(<p,c> in PatternCosts)
    Cut[<p,c>] <= 100 * isCut[<p,c>]; 
  */
}
 
// dual values used to fill in the sub model.
execute FillDuals {
  for(var i in barcodes) {
     Duals[i] = ctFill[i].dual;
  }
}


main {
  var status = 0;
  thisOplModel.generate();

  var RC_EPS = 1.0e-6;

  var masterDef = thisOplModel.modelDefinition;
  var masterCplex = cplex;
  var masterData = thisOplModel.dataElements;
   
  var subSource = new IloOplModelSource("CreatePallets.mod");
  var subDef = new IloOplModelDefinition(subSource);
  var subData = new IloOplDataElements();
  var subCplex = new IloCplex();

  var best;
  var curr = Infinity;
  
  var timeGlobal = masterCplex.getCplexTime();
  var iterate = 0;

  while ( best != curr && iterate<100 ) {
  	//writeln("Iteration ","\t",iterate);
    var start = masterCplex.getCplexTime();
    best = curr;

    var masterOpl = new IloOplModel(masterDef, masterCplex);
    masterOpl.addDataSource(masterData);
    masterOpl.generate();
    masterOpl.convertAllIntVars();
    var numPatterns = 0;
    
    for(var pid in masterOpl.PatternCosts){
    	if(pid.id>numPatterns){
    		numPatterns=pid.id;    	
    	}    
    }
    
    //writeln("Solve master.");
    if ( masterCplex.solve() ) {
      curr = masterCplex.getObjValue();
      //writeln("OBJECTIVE: ","\t",curr);
    } 
    else {
      writeln("No solution!");
      masterOpl.end();
      break;
    }

    subData.MAXWEIGHT = masterOpl.MAXWEIGHT;
    subData.MAXVOLUME = masterOpl.MAXVOLUME;
    subData.PALLETCOST = masterOpl.PALLETCOST;
    subData.DISTANCECOST = masterOpl.DISTANCECOST;
    subData.barcodes = masterOpl.barcodes;
    subData.demand = masterOpl.demand;
    subData.volume = masterOpl.volume;
    subData.weight = masterOpl.weight;
    subData.x = masterOpl.x;
    subData.y = masterOpl.y;
    subData.resistance = masterOpl.resistance;
    subData.ubicacion = masterOpl.ubicacion;
    subData.contamination = masterOpl.contamination;
    subData.nave = masterOpl.nave; 
    subData.resistances = masterOpl.resistances;
    subData.maxWeight = masterOpl.maxWeight;
    subData.maxWeightAbove = masterOpl.maxWeightAbove;    
    
    subData.Duals = masterOpl.Duals;
    for(var i in masterOpl.barcodes) {
      subData.Duals[i] = masterOpl.ctFill[i].dual;
    }

    var subOpl = new IloOplModel(subDef, subCplex);
    subOpl.addDataSource(subData);
    subOpl.generate();

    //writeln("Solve sub.");
    if ( subCplex.solve() ) {
      //writeln("OBJECTIVE: ","\t",subCplex.getObjValue());
    }
    else {
      writeln("No solution!");
      subOpl.end();
      masterOpl.end();
      break;
    }

    if (subCplex.getObjValue() > -RC_EPS) { 
      subOpl.end();
      masterOpl.end();
      break;
    }
   
    // Prepare the next iteration:
    numPatterns = numPatterns + 1;
    
    for(var i in subData.barcodes) {
		if(subOpl.Use[i]>0.001){
			masterData.Patterns.add(numPatterns,i,subOpl.Use[i]);
		}
    }
    masterData.PatternCosts.add(numPatterns,masterOpl.PALLETCOST + subOpl.distance);
    var cont;
    if(subOpl.usesContaminants == 1){
    	cont = "Contaminante";        		
    }else{
    	cont = "Contaminable";        		
    }    
    masterData.PatternInfo.add(numPatterns,subOpl.minx,subOpl.miny,subOpl.maxx,subOpl.maxy,cont);

    subOpl.end();
    masterOpl.end();
 
	iterate = iterate + 1; 
	var end = masterCplex.getCplexTime() - start;
	//writeln("Iteration time lapse: ","\t",end);
	writeln();
  }
  writeln("Relaxed model search end.");
  //writeln("Number of patterns: ", numPatterns);
  writeln();
 
  var intStart = masterCplex.getCplexTime();
  masterCplex.epgap = 0.1
  
  masterOpl = new IloOplModel(masterDef,masterCplex);
  masterOpl.addDataSource(masterData);
  masterOpl.generate();   

  writeln("Solve integer master.");  
  if ( masterCplex.solve() ) {
    writeln("OBJECTIVE: ","\t",masterCplex.getObjValue());
    /*if (Math.abs(masterCplex.getObjValue() - 47)>=0.0001) {
      status = -1;
      writeln("Unexpected objective value");
    }*/
    for(var i in  masterData.PatternCosts) {
      if (masterOpl.Cut[i].solutionValue > 0) {
        //writeln("Pattern ", i.id, " used ", masterOpl.Cut[i].solutionValue << " times");
        //writeln("Content: ");
        writeln("Pattern ", i.id, " used ", masterOpl.Cut[i].solutionValue);
        var finalWeight = 0;        
        var finalVolume = 0;
        for(var j in masterData.Patterns){
        	if(j.id == i.id){
        		//writeln(j.inBarcode, ": ",j.quantity);
        		//writeln(i.id," ",j.inBarcode," ",j.quantity);
        		finalWeight = finalWeight + j.quantity*masterOpl.weight[j.inBarcode];
        		finalVolume = finalVolume + j.quantity*masterOpl.volume[j.inBarcode];
        	}        
        }
        var minx;
        var miny;
        var maxx;
        var maxy;
        var cont;
        for(var k in masterData.PatternInfo){
        	if(k.id == i.id){
        		minx = k.minx;        	
        		miny = k.miny;
        		maxx = k.maxx;
        		maxy = k.maxy;
        		cont = k.contamination;
        	}
        }
        writeln("Pattern: ", i.id, " Weight: ", finalWeight, " Volume: ", finalVolume);
        masterOpl.solutionPallets.add(i.id,masterOpl.Cut[i].solutionValue,finalWeight,finalVolume,cont,5,minx,miny,maxx,maxy);
      }
    } 
  }
  else{
    	writeln("Not solved");   
  }  
  
  var intEnd = masterCplex.getCplexTime()-intStart;
  //writeln("Solution time: ",intEnd);
  //writeln("");
  //writeln("");
  
  ////////////////////////////////////////////////////////////////////////	
  var numPal=0;
  for(var a in masterOpl.solutionPallets){
  	var numUsed = 1;
  	while(numUsed <=a.used){
  		masterOpl.solutionPalletsModif.add(numPal,1,a.weight,a.volume,a.contamination,a.resistance,a.minx,a.miny,a.maxx,a.maxy);
  		for(var k in masterOpl.Patterns){
  			if(k.id==a.id){  			
  				masterOpl.PatternsFinal.add(numPal,k.inBarcode,k.quantity);
  				//writeln(numPal," ",k.inBarcode," ",k.quantity);
  			}
  		}
  	  	numUsed ++;
  		numPal ++;
  	}
  }	
  
  //writeln(masterOpl.PatternsFinal);	
  
  for(var b in masterOpl.barcodes){
  	masterOpl.sumaDemanda[b] = 0;  
  	for(var a in masterOpl.PatternsFinal){
  		if(a.inBarcode==b){ 		
  			masterOpl.sumaDemanda[b] += a.quantity;
  		}			
  	}  
  }
  
  //writeln(masterOpl.sumaDemanda);
  
  for(var b in masterOpl.barcodes){
  	var dif = masterOpl.sumaDemanda[b] - masterOpl.demand[b];
  	for(var a in masterOpl.PatternsFinal){
  		if(a.inBarcode==b){
  			if(dif==0){
  				masterOpl.PatternsModif.add(a.id,a.inBarcode,a.quantity);	
  			}else if(dif<a.quantity){
  				masterOpl.PatternsModif.add(a.id,a.inBarcode,(a.quantity-dif));
  				dif = 0; 			
  			}else if(dif>=a.quantity){
  				//masterOpl.PatternsModif.add(a.id,a.inBarcode,0);
  				dif = dif - a.quantity;			
  			}
  		}	
  	}  
  }
  
  //writeln(masterOpl.PatternsModif);
  writeln("Nuevos");
  for(var i in masterOpl.solutionPalletsModif){
  	var finalWeight = 0;        
    var finalVolume = 0;
    for(var a in masterOpl.PatternsModif){
        if(a.id == i.id){
        	//writeln(j.inBarcode, ": ",a.quantity);
        	finalWeight = finalWeight + a.quantity*masterOpl.weight[a.inBarcode];
        	finalVolume = finalVolume + a.quantity*masterOpl.volume[a.inBarcode];
        }        
    }
        //writeln("Pattern: ", i.id, " Weight: ", finalWeight, " Volume: ", finalVolume);
        masterOpl.solutionPalletsFinal.add(i.id,1,finalWeight,finalVolume,i.contamination,i.resistance,i.minx,i.miny,i.maxx,i.maxy);
  }

  //var numPallet = 0;
  for(var j in masterOpl.solutionPalletsFinal){
  	if(j.weight<800 && j.volume<1.5){
  		masterOpl.subpallets.add(j);
  		for(var i in masterOpl.PatternsModif){
			if(j.id==i.id){
				masterOpl.contents.add(i.id,i.inBarcode,i.quantity,masterOpl.ubicacion[i.inBarcode]);	
				//writeln(i.inBarcode);
				//writeln(masterOpl.ubicacion[i.inBarcode]);
				//writeln("contents ", i.id," ",i.inBarcode," ",i.quantity);
			}	
  		}
  	}else{  	
  		//masterOpl.palletInfo.add(j.id, i.weight, i.volume,masterOpl.lista);
  		for(var i in masterOpl.PatternsModif){
			if(j.id==i.id){
				masterOpl.contentsDef.add(i.id,i.inBarcode,i.quantity,masterOpl.ubicacion[i.inBarcode]);
				//writeln("contentsDef ", i.id," ",i.inBarcode," ",i.quantity);
			}	
  		}
 	}  	
  }
  //writeln(masterOpl.contents);
  //writeln(masterOpl.contentsDef);
  //writeln(masterOpl.subpallets);
  
  for(var b in masterOpl.barcodes){
  	masterOpl.sumaDemanda[b] = 0;  
  	for(var a in masterOpl.contents){
  		if(a.barcode==b){ 		
  			masterOpl.sumaDemanda[b] += a.quantity;
  		}			
  	}
  	//writeln(masterOpl.sumaDemanda[b]);  
  }

  
  var newSource = new IloOplModelSource("NewPallets.mod");
  var newDef = new IloOplModelDefinition(newSource);
  var newData = new IloOplDataElements();
  var newCplex = new IloCplex();
  
  newData.MAXWEIGHT = masterOpl.MAXWEIGHT;
  newData.MAXVOLUME = masterOpl.MAXVOLUME;
  newData.PALLETCOST = masterOpl.PALLETCOST;
  newData.DISTANCECOST = masterOpl.DISTANCECOST;
  newData.barcodes = masterOpl.barcodes;
  newData.demand = masterOpl.sumaDemanda;
  newData.volume = masterOpl.volume;
  newData.weight = masterOpl.weight;
  newData.x = masterOpl.x;
  newData.y = masterOpl.y;
  newData.resistance = masterOpl.resistance;
  newData.ubicacion = masterOpl.ubicacion;
  newData.contamination = masterOpl.contamination;
  newData.nave = masterOpl.nave; 
  newData.resistances = masterOpl.resistances;
  newData.maxWeight = masterOpl.maxWeight;
  newData.maxWeightAbove = masterOpl.maxWeightAbove;
  newData.subpallets = masterOpl.subpallets;
  newData.contents = masterOpl.contents;
  newData.numPallets = 25;
  
  var newOpl = new IloOplModel(newDef, newCplex);
  newOpl.addDataSource(newData);
  newOpl.generate();

  writeln("Solve new.");
  if ( newCplex.solve() ) {
      //writeln("OBJECTIVE: ","\t",newCplex.getObjValue());
      //writeln(newOpl.assign);
  }else {
    writeln("No solution!");
    newOpl.end();
    masterOpl.end();
  }
  
  //writeln(masterOpl.contentsDef);
  //writeln(newOpl.contentsNew);
  //masterData.contents=newOpl.contentsNew;
  //writeln(masterOpl.palletInfo);
  //masterOpl.palletInfo.add(newOpl.palletInfo);
  //writeln(masterOpl.palletInfo);
  
  var ofile = new IloOplOutputFile("SOLUCION2.dat");
  var timeGlobalFin = masterCplex.getCplexTime() - timeGlobal;
  
  var size1 = (masterOpl.solutionPalletsFinal.size - masterOpl.subpallets.size) + newOpl.palletInfo.size;

  ofile.writeln("maximum running time: "+timeGlobalFin);
  ofile.writeln("Núemro de pallets: ",size1);
	
	//ofile.writeln("FO: ", cplex.getObjValue());
	ofile.writeln("Pallets GC");
	for(var i in masterOpl.contentsDef){
		writeln(i.barcode," ",i.quantity);
		ofile.writeln(i.id," ",i.barcode," ",i.quantity);
	}
	ofile.writeln("Pallets New");
	for(var i in newOpl.contentsNew){
		ofile.writeln(i.id," ",i.barcode," ",i.quantity);	
	}
	
	ofile.close();
  
  
  
  
  
  newOpl.end();
  masterOpl.end();  
  status;
  
  
   
}



 