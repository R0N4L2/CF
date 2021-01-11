tuple param_tuple{
	string nombre;
	int valor;
}
{param_tuple} parametros = ...;

{string} nombre_param = {n | <n,v> in parametros};
int valor_param[nombre_param] = [n : v | <n,v> in parametros];
int numGrupos = valor_param["NUM_GRUPOS"];
int maxLocales = valor_param["MAX_LOCAL"];
int maxFurgones = valor_param["MAX_FURGON"];
range grupos = 1..numGrupos;

tuple locales_tuple{
	int id;
	float latitud;
	float longtud;
	float precio;
	float penal;
	string subzona;
}

{locales_tuple} infoLocales = ...;
{int} locales = {i | <i,la,lo,c,p,s> in infoLocales};
float latitud[locales] = [i : la | <i,la,lo,c,p,s> in infoLocales];
float longitud[locales] = [i : lo | <i,la,lo,c,p,s> in infoLocales];

tuple distancias_tuple{
	int local1;
	int local2;
	float distancia;
}
{distancias_tuple} infoDistancias = ...;
tuple localesPares_tuple{
	int local1;
	int local2;
}
{localesPares_tuple} parDistancia = {<l1,l2> | <l1,l2,d> in infoDistancias};
float distancia[parDistancia] = [<l1,l2> : d | <l1,l2,d> in infoDistancias];

tuple num_furgones_tuple{
	int local;
	int cantidad;
}
{num_furgones_tuple} infoFurgones = ...;
int cantidadFurgones[locales] = [l : c | <l,c> in infoFurgones];

dvar boolean asignarGrupo[grupos][locales];
dvar boolean activo[grupos][parDistancia];
dvar float+ maxDistancia[grupos];
dvar boolean grupoActivo[grupos];

minimize sum(g in grupos)maxDistancia[g] + sum(g in grupos)grupoActivo[g];

subject to{
	
	forall(g in grupos){
		sum(l in locales)asignarGrupo[g][l] <= maxLocales;
		sum(l in locales)(asignarGrupo[g][l] * cantidadFurgones[l]) <= maxFurgones;
		//(maxCombinacion / sum(l in locales)(asignarGrupo[g][l])) <= sum(l in locales)(asignarGrupo[g][l] * cantidadFurgones[l]);
	}	
		
	forall(l in locales)
		sum(g in grupos)asignarGrupo[g][l] == 1;
	
	forall(g in grupos, <l1,l2> in parDistancia){
		asignarGrupo[g][l1] + asignarGrupo[g][l2] >= 2 * activo[g][<l1,l2>];
		asignarGrupo[g][l1] + asignarGrupo[g][l2] - 1 <= activo[g][<l1,l2>];
	}
	
	forall(g in grupos, <l1,l2> in parDistancia)
		maxDistancia[g] >= distancia[<l1,l2>] * activo[g][<l1,l2>];
		
	forall(g in grupos, l in locales)
		asignarGrupo[g][l] <= grupoActivo[g];
}

tuple solucion_tuple{
	int local;
	int grupo;
}
{solucion_tuple} solucion = {<l,g> | l in locales, g in grupos : asignarGrupo[g][l] > 0};

tuple combi_tuple{
	int grupo;
	int combinacion;
}
{combi_tuple} combinacion = {<g,sum(l in locales)(asignarGrupo[g][l]) * sum(l in locales)(asignarGrupo[g][l]*cantidadFurgones[l])> | g in grupos};

execute{
	writeln(solucion);
	writeln(combinacion);
}