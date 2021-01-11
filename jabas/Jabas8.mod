/*********************************************
 * OPL 12.8.0.0 Model
 * Author: ronal
 * Creation Date: 31-10-2019 at 17:08:56
 *********************************************/
/*********************************************
 * OPL 2.8.0.0 Model
 * Author: ronal
 * Creation Date: 24-0-209 at 23:0:24
 *********************************************/
 

tuple jabaInformacionTipo {
	string jaba;
	float peso;
	float alto;
	int demanda;
	float x;
	float y;
}
{jabaInformacionTipo} jabaInformacion = ...;
{string} jabas = {ji.jaba | ji in jabaInformacion};
int maxDemanda=max(ji in jabaInformacion) ji.demanda;
//float maximoY = max(ji in jabaInformacion) ji.y;


tuple parametrosTipo{
	string parametro;
	float valor;
}
{parametrosTipo} parametros=...;
{string} nombreParametro = {p | <p,v> in parametros};
float parametroValor[nombreParametro] = [p:v | <p,v> in parametros];
float AltoMax=parametroValor["cantidadJabas"]*parametroValor["altoMaximo"];

tuple palletExtraTipo {
	int codigoPallet;
	float altoPermitido;
	float pesoPermitido;
}
{palletExtraTipo} palletExtra=...;
int maxCodigoPallet = max(pe in palletExtra) pe.codigoPallet;
int maxPalletsPosibles = 0;
execute{
	if (maxCodigoPallet>0){
		maxPalletsPosibles = maxCodigoPallet;
	}else{
		maxPalletsPosibles = Math.floor(parametroValor["PalletTotales"]);
	}
}		
range numeroPallet = 1..maxPalletsPosibles;
float maxPesoPallet[plt in numeroPallet] = 0;
float maxAltoPallet[plt in numeroPallet] = 0;
execute{	
	if (maxCodigoPallet>0){
		for (var pe in palletExtra){
				maxPesoPallet[pe.codigoPallet]=pe.pesoPermitido;
				maxAltoPallet[pe.codigoPallet]=pe.altoPermitido;
		}
	}else{	
		for (var plt in numeroPallet){
				maxPesoPallet[plt]=parametroValor["pesoMaximo"];
				maxAltoPallet[plt]=AltoMax;
		}
	}				
}
float maxPalletJabas[ji in jabaInformacion] = 0;
execute{
for (var ji in jabaInformacion){
			maxPalletJabas[ji]=ji.demanda*Math.max(ji.alto/AltoMax,ji.peso/parametroValor["pesoMaximo"]);}}
/*
int cantJabas=sum(ji in jabaInformacion)1;		
execute{cantJabas=Math.min(cantJabas,maxPalletsPosibles)};
reversed {float} s={maxPalletJabas[ji]|ji in jabaInformacion};
range maxOrden = 1..cantJabas;
float ordenados[i in maxOrden]=item(s,i-1);
execute{writeln(ordenados);}	
*/
execute{
	cplex.tilim = 60;
	cplex.epgap=.1;
}

//Begin
//Variables
dvar float+ palletAlturaEnviado[numeroPallet];
dvar boolean esAsignadaJabaAPallet[jabas][numeroPallet];
dvar int+ cantidadJabaAsignadaPallet[jabas][numeroPallet] in 0..maxDemanda;
/*
dvar float+ maxy[numeroPallet];
dvar float+ miny[numeroPallet];
*/
dvar float+ AlturaSinLlenar;
//funcion de costo por no envio de jabas
dexpr float costoAlturaSinEnviar = parametroValor["costoNoEnvio"] * AlturaSinLlenar; 
//costo de movimiento de cada pallet
//dexpr float costoDistancia = sum(plt in numeroPallet)parametroValor["costoTransporte"] * (maxy[plt] - miny[plt]);
//costo de cumplimiento de las mayores demandas
//dexpr float costoDemanda = sum(ji in jabaInformacion)maxPalletJabas[ji]*(ji.demanda-sum(plt in numeroPallet)cantidadJabaAsignadaPallet[ji.jaba][plt]);
//costo de llenado de pallets
dexpr float costoDistribucion=sum(ji in jabaInformacion)maxPalletJabas[ji]*sum(plt in numeroPallet)esAsignadaJabaAPallet[ji.jaba][plt];
//Objective
minimize costoAlturaSinEnviar+costoDistribucion;//+costoDemanda;//costoAlturaSinEnviar+costoDistancia+

//Constraints
subject to {
	sum(plt in numeroPallet) (maxAltoPallet[plt]-palletAlturaEnviado[plt]) == AlturaSinLlenar;	
	//covertura de medidas por pallet
	forall (plt in numeroPallet){
		sum(ji in jabaInformacion)
			ji.peso * cantidadJabaAsignadaPallet[ji.jaba][plt]<=maxPesoPallet[plt];
		sum(ji in jabaInformacion) ji.alto * cantidadJabaAsignadaPallet[ji.jaba][plt] == palletAlturaEnviado[plt];
		palletAlturaEnviado[plt]<=maxAltoPallet[plt];	
		//restirccion obvia, de que el maximo tiene que ser mayo que el minimo
		//miny[plt] <=maxy[plt];
	}		
	//covertura de demanda por articulo
	forall(ji in jabaInformacion){
		sum(plt in numeroPallet)
			cantidadJabaAsignadaPallet[ji.jaba][plt] <= ji.demanda;
  	}		  
	forall(plt in numeroPallet, ji in jabaInformacion){
		//unicidad de variable 	cantidadJabaAsignadaPallet y esAsignadaJabaAPallet	
		cantidadJabaAsignadaPallet[ji.jaba][plt]<=esAsignadaJabaAPallet[ji.jaba][plt]*ji.demanda;
		cantidadJabaAsignadaPallet[ji.jaba][plt]>=esAsignadaJabaAPallet[ji.jaba][plt];
		//restriccion de las variables de distancia x e y para cada pallet y jaba
		//maxy[plt]>=esAsignadaJabaAPallet[ji.jaba][plt]*ji.y;
		//miny[plt]<=maximoY+esAsignadaJabaAPallet[ji.jaba][plt]*(ji.y-maximoY);	
	}	
	/*
	forall(ji in jabaInformacion,i in numeroPallet:maxPalletJabas[ji]==ordenados[i]&&maxDemanda==1){
		sum(plt in numeroPallet)
			cantidadJabaAsignadaPallet[ji.jaba][plt] == ji.demanda;	
		sum(plt in numeroPallet)
		  esAsignadaJabaAPallet[ji.jaba][plt]==1;		
	}
	*/
}
//End 

tuple jabasXPalletTipo{
	string codigoJaba;
	float pesoJaba;
	float alturaJaba;
	int cantidadJabas;
	int codigoPallet;
	float x;
	float y;	
}
{jabasXPalletTipo} jabasNPallet = {<ji.jaba,ji.peso,ji.alto,cantidadJabaAsignadaPallet[ji.jaba][plt],plt,ji.x,ji.y> |plt in numeroPallet, ji in jabaInformacion:esAsignadaJabaAPallet[ji.jaba][plt]>= 0.9};
execute{writeln(jabasNPallet);}
 