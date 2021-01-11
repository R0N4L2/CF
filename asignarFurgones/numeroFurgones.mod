tuple param_tuple{
	string nombre;
	int valor;
}

{param_tuple} parametros = ...;

{string} nombre_param = {n | <n,v> in parametros};
int valor_param[nombre_param] = [n : v | <n,v> in parametros];
int minFrio = valor_param["MIN_FRIO"];
int minSeco = valor_param["MIN_SECO"];

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
	int indice;
	string id;
	string tipo;
	int capacidad;
	int cantidad;
}

{furgones_tuple} infoFurgones = ...;

tuple pedido_tuple{
	int id_local;
	float num_frios;
	float num_secos;
	float num_total;
}

{pedido_tuple} infoPedido = ...;

{int} locales = {i | <i,la,lo,c,p,s> in infoLocales};
float costoFlete[locales] = [i : c | <i,la,lo,c,p,s> in infoLocales];
float penalPallet[locales] = [i : p | <i,la,lo,c,p,s> in infoLocales];

{int} indicesFurgones = {ix | <ix,id,t,c,k> in infoFurgones};
string furgonesDisponibles[indicesFurgones] = [ix : id | <ix,id,t,c,k> in infoFurgones];
{int} furgonesFrios = {ix | <ix,id,t,c,k> in infoFurgones : t == "F"};
{int} furgonesSecos = {ix | <ix,id,t,c,k> in infoFurgones : t == "S"};
int capacidad[indicesFurgones] = [ix : c | <ix,id,t,c,k> in infoFurgones];
int cantidad[indicesFurgones] = [ix : k | <ix,id,t,c,k> in infoFurgones];

float demandaSeco[locales] = [i : ns | <i,nf,ns,nt> in infoPedido];
float demandaFrio[locales] = [i : nf | <i,nf,ns,nt> in infoPedido];


dvar int+ cantidadLocal[local in locales][furgon in indicesFurgones] in 0..cantidad[furgon];
dvar int+ cantidadLocalSubcontratar[local in locales][furgon in indicesFurgones];
dvar boolean tipoFurgonActivo[indicesFurgones];

minimize sum(local in locales, furgon in indicesFurgones) cantidadLocal[local][furgon] + sum(local in locales, furgon in indicesFurgones) 2 * cantidadLocalSubcontratar[local][furgon]; //+ sum(furgon in indicesFurgones)tipoFurgonActivo[furgon];

subject to{
	forall(local in locales)
	sum(furgon in furgonesFrios) (cantidadLocal[local][furgon]*capacidad[furgon] + cantidadLocalSubcontratar[local][furgon]*capacidad[furgon]) >= demandaFrio[local];
	//sum(furgon in furgonesFrios) (cantidadLocal[local][furgon]*capacidad[furgon]) >= demandaFrio[local];
	
	forall(local in locales)
	sum(furgon in furgonesSecos) (cantidadLocal[local][furgon]*capacidad[furgon] + cantidadLocalSubcontratar[local][furgon]*capacidad[furgon]) >= demandaSeco[local];
	//sum(furgon in furgonesSecos) (cantidadLocal[local][furgon]*capacidad[furgon]) + a >= demandaSeco[local];
	  
	forall(furgon in indicesFurgones)
	  sum(local in locales) cantidadLocal[local][furgon] <= tipoFurgonActivo[furgon] * cantidad[furgon];
		
	forall(furgon in furgonesFrios: furgon > minFrio)
		tipoFurgonActivo[furgon-1] >= tipoFurgonActivo[furgon];
	
	forall(furgon in furgonesSecos: furgon > minSeco)
		tipoFurgonActivo[furgon-1] >= tipoFurgonActivo[furgon];
}

tuple solucion_tuple{
	string furgon;
	int local;
	int cantidad;
}
{solucion_tuple} solucion = {<furgonesDisponibles[f],l,cantidadLocal[l][f]> | l in locales, f in indicesFurgones : cantidadLocal[l][f]>0};
{solucion_tuple} solucion_subcontratar = {<furgonesDisponibles[f],l,cantidadLocalSubcontratar[l][f]> | l in locales, f in indicesFurgones : cantidadLocalSubcontratar[l][f]>0};

execute{
	solucion;
	solucion_subcontratar;
}
