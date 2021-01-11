tuple param_tuple{
	string nombre;
	int valor;
}

{param_tuple} parametros = ...;

tuple locales_tuple{
	int id;
	float latitud;
	float longtud;
	float precio;
	float penal;
	string subzona;
}

{locales_tuple} infoLocales = ...;

tuple furgones_tuple{
	string id;
	string tipo;
	int capacidad;
}

{furgones_tuple} infoFurgones = ...;

tuple pedido_tuple{
	int id_local;
	int num_frios;
	int num_secos;
	int num_total;
}

{pedido_tuple} infoPedido = ...;

{string} nombre_param = {n | <n,v> in parametros};
int valor_param[nombre_param] = [n : v | <n,v> in parametros];
int maxLocales = valor_param["MAX_LOCALES"];
int maxFurgones = valor_param["MAX_FURGONES"];
int costoDist = valor_param["COSTO_DISTANCIA"];
int maxDivision = valor_param["MAX_DIVISION"];

{int} locales = {i | <i,la,lo,c,p,s> in infoLocales};
float costoFlete[locales] = [i : c | <i,la,lo,c,p,s> in infoLocales];
float penalPallet[locales] = [i : p | <i,la,lo,c,p,s> in infoLocales];

{string} furgonesDisponibles = {i | <i,t,c> in infoFurgones};
{string} furgonesSecosDisponibles = {i | <i,t,c> in infoFurgones : t == "S"};
{string} furgonesFriosDisponibles = {i | <i,t,c> in infoFurgones : t == "F"};
string tipoFurgon[furgonesDisponibles] = [i : t | <i,t,c> in infoFurgones];
int capacidad[furgonesDisponibles] = [i : c | <i,t,c> in infoFurgones];

float demandaSeco[locales] = [i : ns | <i,nf,ns,nt> in infoPedido];
float demandaFrio[locales] = [i : nf | <i,nf,ns,nt> in infoPedido];

tuple combinacionType{
	int local;
	string furgon;
}
//combinaciones factibles
{combinacionType} localFurgon = ...;
{combinacionType} localFurgonFrio = {<l,f> | <l,f> in localFurgon: f in furgonesFriosDisponibles};
{combinacionType} localFurgonSeco = {<l,f> | <l,f> in localFurgon: f in furgonesSecosDisponibles};
{string} furgonesFrios = {f | <l,f> in localFurgonFrio};

tuple localesPares_tuple{
	int local1;
	int local2;
}
{localesPares_tuple} localesIncompatibles = ...;

//{string} localesUnico = ...;

tuple distancias_tuple{
	int local1;
	int local2;
	float distancia;
}
{distancias_tuple} infoDistancias = ...;
{localesPares_tuple} parDistancia = {<l1,l2> | <l1,l2,d> in infoDistancias};
float distancia[parDistancia] = [<l1,l2> : d | <l1,l2,d> in infoDistancias];

//variables de decision
//Revisar el conjunto, no todos son fríos
dvar int+ cargarFrio[<local,furgon> in localFurgonFrio];// in 0..demandaFrio[local];
dvar int+ cargarSeco[<local,furgon> in localFurgon];// in 0..demandaSeco[local];
dvar boolean asignarFurgon[localFurgon];
dvar boolean asignarFurgonFrio[localFurgon];
dvar boolean asignarFurgonSeco[localFurgon];
dvar float+ costoFurgon[furgonesDisponibles]; //o solo furgon?
//dvar int+ envioVacio[furgonesDisponibles]; //o solo furgon
//No envío de pallets
dvar int+ noCargaFrio[local in locales];// in 0..demandaFrio[local];
dvar int+ noCargaSeco[local in locales];// in 0..demandaSeco[local];
//Distancia recorrida
//dvar float distancia_furgon[furgonesDisponibles]; 
dvar boolean furgonUtilizado[furgonesDisponibles];
dvar boolean furgonFrioUtilizado[furgonesFriosDisponibles];
dvar boolean furgonSecoUtilizado[furgonesSecosDisponibles];

dvar int+ furgonLocalesAsignados[locales];
dvar int+ furgonLocalesFrios[locales];
dvar int+ furgonLocalesSecos[locales];

dvar boolean todoFrioAFurgon[locales];
dvar boolean todoSecoAFurgon[locales];
dvar boolean todoAFurgon[locales];

dexpr float costoFleteTotal = sum(f in furgonesDisponibles)costoFurgon[f];
dexpr float penalNoEntregado = 5000*sum(local in locales)penalPallet[local]*(noCargaFrio[local] + noCargaSeco[local]);

dexpr int numAsignaciones = sum(furgon in furgonesDisponibles)furgonUtilizado[furgon];
dexpr int numAsignacionFrio = sum(furgon in furgonesFriosDisponibles)furgonUtilizado[furgon];
dexpr int numAsignacionSeco = sum(furgon in furgonesSecosDisponibles)furgonUtilizado[furgon];
dexpr int numFurgonesLocales = sum(local in locales)furgonLocalesAsignados[local];
dexpr int bonoTodoAFurgon = 20 * sum(local in locales)(todoFrioAFurgon[local]+todoSecoAFurgon[local]);
dexpr int bonoTodoAFurgonCompleto = 40 * sum(local in locales)todoAFurgon[local];

minimize
  numAsignaciones * 400
  //numAsignacionFrio * 400
  //+ numAsignacionSeco * 100
  - bonoTodoAFurgon
  //- bonoTodoAFurgonCompleto
  //+ numFurgonesLocales * 350
  //+ costoFleteTotal
  + penalNoEntregado;

subject to{
	// Cargar furgones frios
	forall(local in locales)
	  	//sum(<local,furgon> in localFurgonFrio)(cargarFrio[<local,furgon>]) >= demandaFrio[local];
		sum(<local,furgon> in localFurgonFrio)(cargarFrio[<local,furgon>]) + noCargaFrio[local] == demandaFrio[local];
	
	// Cargar furgones secos
	forall(local in locales)
		//sum(<local,furgon> in localFurgon)(cargarSeco[<local,furgon>]) >= demandaSeco[local];
		sum(<local,furgon> in localFurgon)(cargarSeco[<local,furgon>]) + noCargaSeco[local] == demandaSeco[local];
	
	// Costo furgon como máximo flete de local a visitar
	// Ya no se calcula así, se calcula basado en distancia recorida
	forall(<local,furgon> in localFurgon)
		costoFurgon[furgon] >= costoFlete[local]*asignarFurgon[<local,furgon>];
	
	//Carga en caso de asignación 
	forall(<local,furgon> in localFurgonFrio){
		cargarFrio[<local,furgon>] <= asignarFurgon[<local,furgon>] * demandaFrio[local];
		cargarFrio[<local,furgon>] <= asignarFurgonFrio[<local,furgon>] * demandaFrio[local];
		//asignarFurgon[<local,furgon>] <=  cargarFrio[<local,furgon>] + cargarSeco[<local,furgon>];
	}	
	forall(<local,furgon> in localFurgon){
		cargarSeco[<local,furgon>] <= asignarFurgon[<local,furgon>] * demandaSeco[local];
		cargarSeco[<local,furgon>] <= asignarFurgonSeco[<local,furgon>] * demandaSeco[local];
		//asignarFurgon[<local,furgon>] <= cargarSeco[<local,furgon>];
	}	
	// Carga de pallets inferior a la capacidad
	forall(furgon in furgonesDisponibles)
		sum(<local,furgon> in localFurgonFrio)(cargarFrio[<local,furgon>] + cargarSeco[<local,furgon>]) <= capacidad[furgon];
	
	forall(furgon in furgonesDisponibles)
		sum(<local,furgon> in localFurgon)cargarSeco[<local,furgon>] <= capacidad[furgon];
		
	//Máximo número de locales a visitar por furgón
	forall(<local,furgon> in localFurgon)
		asignarFurgon[<local,furgon>] <= furgonUtilizado[furgon];
	
	forall(furgon in furgonesDisponibles)
		sum(<local,furgon> in localFurgon)asignarFurgon[<local,furgon>] <= maxLocales*furgonUtilizado[furgon];
	/*	
	forall(furgon in furgonesFriosDisponibles)
		sum(<local,furgon> in localFurgonFrio)asignarFurgonFrio[<local,furgon>] <= maxLocales*furgonFrioUtilizado[furgon];	
	
	forall(furgon in furgonesSecosDisponibles)
		sum(<local,furgon> in localFurgonSeco)asignarFurgonSeco[<local,furgon>] <= maxLocales*furgonSecoUtilizado[furgon];	
	*/
	forall(local in locales)
		sum(<local,furgon> in localFurgon)asignarFurgon[<local,furgon>] == furgonLocalesAsignados[local];

	//forall(local in locales)
		//furgonLocalesAsignados[local] <= maxFurgones;

	forall(local in locales)
		sum(<local,furgon> in localFurgonFrio)asignarFurgonFrio[<local,furgon>] == furgonLocalesFrios[local];
		
	forall(local in locales)
		sum(<local,furgon> in localFurgon)asignarFurgonSeco[<local,furgon>] == furgonLocalesSecos[local];
		
	forall(local in locales)
		sum(<local,furgon> in localFurgonFrio)asignarFurgon[<local,furgon>] <= maxDivision;
	
	forall(local in locales)
		sum(<local,furgon> in localFurgonSeco)asignarFurgon[<local,furgon>] <= maxDivision;
		
	forall(local in locales)
		furgonLocalesFrios[local] <= 1 + (1 - todoFrioAFurgon[local])*10;
	
	forall(local in locales)
		furgonLocalesSecos[local] <= 1 + (1 - todoSecoAFurgon[local])*10;
		
	forall(local in locales)
		furgonLocalesAsignados[local] <= 1 + (1 - todoAFurgon[local])*10;
		
	//Locales incompatibles no pueden ir en el mismo furgon
	forall(<local1,local2> in localesIncompatibles, <local1,furgon> in localFurgon, <local2,furgon> in localFurgon)
		asignarFurgon[<local1,furgon>] + asignarFurgon[<local2,furgon>] <= 1;
	
	//Definir distancia entre locales
	//forall(furgon in furgonesDisponibles)
	//	distancia_furgon[furgon] = sum(<local1,furgon> in localFurgon, <local2,furgon> in localFurgon : <local1,local2> in parDistancia) ;
}

tuple solucion_tuple{
	int local;
	string furgon;
	float costo;
}
{solucion_tuple} asignacion = {<l,f,costoFurgon[f]> | <l,f> in localFurgon : asignarFurgon[<l,f>] > 0};

tuple carga_tuple{
	int local;
	string furgon;
	string tipoFurgon;
	string tipoPallet;
	int capacidad;
	float cantidad;
}
{carga_tuple} carga = {<l,f,tipoFurgon[f],"F",capacidad[f],cargarFrio[<l,f>]> | <l,f> in localFurgonFrio : cargarFrio[<l,f>] > 0}
					union {<l,f,tipoFurgon[f],"S",capacidad[f],cargarSeco[<l,f>]> | <l,f> in localFurgon : cargarSeco[<l,f>] > 0};

execute{
	carga;
	asignacion;
}