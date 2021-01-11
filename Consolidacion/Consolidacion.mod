/*********************************************
 * OPL 12.7.1.0 Model
 * Author: jwood
 * Creation Date: Mar 13, 2018 at 8:46:08 AM
 *********************************************/

{string} subZones = {"SZ9"};
{string} fulgones = ...;
int esFrio[fulgones] = ...;
int capacidad[fulgones] = ...;
{string} destinos = ...;
{string} destinosSolos = ...;
int pallets[destinos] = ...;
int palletsFrios[destinos] = ...;
int codigoDestino[destinos] = ...;
string subZona[destinos] = ...;
float costoDestino[destinos] = ...;
float costoActual[destinos] = ...;
{string} subZonas = {subZona[d] | d in destinos: subZona[d] in subZones};

tuple fulgonDestinoType{
	string destino;
	string fulgon;
}
{string} fulgonesUtilizados = ...;
{string} fulgonesDisponibles = fulgones diff fulgonesUtilizados;
{fulgonDestinoType} secos = {<d,f> | d in destinos, f in fulgonesDisponibles: pallets[d] > 0 && subZona[d] in subZones}; //secos can go in anything.
{fulgonDestinoType} frios = {<d,f> | d in destinos, f in fulgonesDisponibles: palletsFrios[d] > 0 && esFrio[f] > 0 && subZona[d] in subZones}; //secos can go in anything.

float maxCost = max(d in destinos) costoDestino[d];

dvar int+ asignar[<d,f> in secos] in 0..pallets[d];
dvar int+ asignarFrios[<d,f> in frios] in 0..palletsFrios[d];
dvar float+ noMandados[d in destinos] in 0..pallets[d];
dvar float+ noMandadosFrios[d in destinos] in 0..palletsFrios[d];
dvar boolean fulgonVaASubZona[fulgonesDisponibles][subZonas];
dvar boolean fulgonVaADestino[fulgonesDisponibles][destinos];
dvar float+ costoFulgon[fulgonesDisponibles] in 0..maxCost;

dexpr float costoMandar = sum(f in fulgonesDisponibles) costoFulgon[f];
dexpr float costoNoMandar = 56 * sum(d in destinos) (noMandados[d] + noMandadosFrios[d]);
dexpr float costoUsarFrio = sum(f in fulgonesDisponibles,d in destinos: esFrio[f] == 1 && subZona[d] in subZones) fulgonVaASubZona[f][subZona[d]];

execute {
	cplex.tilim = 400;
	cplex.threads = 4;
}
minimize 
	costoMandar + costoNoMandar + costoUsarFrio;
	
subject to {

	//each destination must have its pallets assigned to a fulgon
	forall (d in destinos: pallets[d] > 0 && subZona[d] in subZones)
		(sum(f in fulgonesDisponibles) asignar[<d,f>]) + noMandados[d] == pallets[d];
		//sum(f in fulgones) asignar[<d,f>] == pallets[d];
		
	//the cold pallets must be assigned to only cold fulgones
	forall (d in destinos: palletsFrios[d] > 0 && subZona[d] in subZones)
		(sum(<d,f> in frios) asignarFrios[<d,f>]) + noMandadosFrios[d] == palletsFrios[d];
		//sum(<d,f> in frios) asignarFrios[<d,f>] == palletsFrios[d];
		
	//determine if a fulgon is going to a customer
	forall(d in destinos, f in fulgonesDisponibles: subZona[d] in subZones)
	  	(capacidad[f] + 1) * fulgonVaADestino[f][d] >= sum(<d,f> in frios) asignarFrios[<d,f>] 
	  		+ sum(<d,f> in secos) asignar[<d,f>];
		
	//each fulgon can have no more than 4 destinos
	forall(f in fulgonesDisponibles)
		sum(d in destinos) fulgonVaADestino[f][d] <= 4;
		
	//determine when a fulgon goes to a sub zone
	forall (f in fulgonesDisponibles, z in subZonas)
		capacidad[f] * fulgonVaASubZona[f][z] >= sum(<d,f> in secos: subZona[d] == z) asignar[<d,f>]
			+ sum(<d,f> in frios: subZona[d] == z) asignarFrios[<d,f>];
		
	//a fulgon can only go to one sub zone
	forall (f in fulgonesDisponibles)
		sum(z in subZonas) fulgonVaASubZona[f][z] <= 1;
	
	//the cost of a fulgon is the maximum of the zones it goes to.
	forall (f in fulgonesDisponibles, d in destinos: subZona[d] in subZones)
		costoFulgon[f] >= costoDestino[d] * fulgonVaADestino[f][d];
		
	//for the destinations that are exclusive, only the one customer may go.
	forall (d in destinosSolos, f in fulgonesDisponibles: subZona[d] in subZones)
		(sum(<d,f> in secos) asignar[<d,f>] + sum(<d,f> in frios) asignarFrios[<d,f>] >= 1) 
			=> (sum(<d2,f> in secos: d2 != d) asignar[<d2,f>] + sum(<d2,f> in frios: d2 != d) asignarFrios[<d2,f>] == 0);
		
	//each fulgon may not have more than the capacity in pallets
	forall (f in fulgonesDisponibles)
		sum(<d,f> in secos) asignar[<d,f>] + sum(<d,f> in frios) asignarFrios[<d,f>] <= capacidad[f];
		
	//if a fulgon is used, the quantity assigned to the next fulgon is the same or smaller, reduces circular
	forall(f1, f2 in fulgonesDisponibles: ord(fulgonesDisponibles,f1) == ord(fulgonesDisponibles,f2) - 1 && esFrio[f1] == 0 && esFrio[f2] == 0)
		sum(<d,f1> in secos) asignar[<d,f1>] >= sum(<d,f1> in secos) asignar[<d,f2>];
		
	//if a fulgon is used, the quantity assigned to the next fulgon is the same or smaller, reduces circular
	forall(f1, f2 in fulgonesDisponibles: ord(fulgonesDisponibles,f1) == ord(fulgonesDisponibles,f2) - 1 && esFrio[f1] == 1 && esFrio[f2] == 1)
		sum(<d,f1> in secos) asignar[<d,f1>] + sum(<d2,f1> in frios) asignarFrios[<d2,f1>] 
			>= sum(<d,f2> in secos) asignar[<d,f2>] + sum(<d2,f2> in frios) asignarFrios[<d2,f2>]; 
	
}

tuple resultadosType{
	int local;
	string fulgon;
	int secos;
	int frios;
	string subzona;
	int esFrio;
}
int cantFrios[d in destinos][f in fulgonesDisponibles] = sum(<d,f> in frios) asignarFrios[<d,f>];
int cantSecos[d in destinos][f in fulgonesDisponibles] = sum(<d,f> in secos) asignar[<d,f>];
int cantTotal[d in destinos][f in fulgonesDisponibles] = cantFrios[d][f] + cantSecos[d][f];

{resultadosType} resultados = {<codigoDestino[d],f,cantSecos[d][f],cantFrios[d][f],subZona[d],esFrio[f]> | d in destinos, f in fulgonesDisponibles : cantTotal[d][f] > 0};
int asignaciones[f in fulgonesDisponibles] = sum(<d1,f> in secos) asignar[<d1,f>] + sum(<d2,f> in frios) asignarFrios[<d2,f>];
int asignacionesDest[d in destinos] = sum(<d,f1> in secos) asignar[<d,f1>] + sum(<d,f2> in frios) asignarFrios[<d,f2>];


execute{
	writeln(resultados);
	writeln(cantTotal);
	writeln(asignaciones);
	writeln(asignacionesDest);
}


