/*********************************************
 * OPL 12.8.0.0 Model
 * Author: ronal
 * Creation Date: 30-10-2019 at 19:27:39
 *********************************************/
 tuple parametrosTipo{
	string parametro;
	float valor;
}
{parametrosTipo} parametros=...;
{string} nombreParametro = {p | <p,v> in parametros};
float parametroValor[nombreParametro] = [p:v | <p,v> in parametros];
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
float pesoTotal = sum(ji in jabaInformacion) ji.peso * ji.demanda;
float alturaTotal = sum(ji in jabaInformacion) ji.alto * ji.demanda;
/*
float maximoX = max(ji in jabaInformacion) ji.x;
float maximoY = max(ji in jabaInformacion) ji.y;
float minimoX = min(ji in jabaInformacion) ji.x;
float minimoY = min(ji in jabaInformacion) ji.y;
*/
float AltoMax=parametroValor["cantidadJabas"]*parametroValor["altoMaximo"];
/*
tuple palletExtraTipo {
	int codigoPallet;
	float altoPermitido;
	float pesoPermitido;
}
{palletExtraTipo} palletExtra=...;
int maxCodigoPallet = max(pe in palletExtra) pe.codigoPallet;
*/
int maxPalletsPosibles = 0;
execute{
	maxPalletsPosibles = Math.ceil(1.2*Math.max(Math.ceil(alturaTotal/AltoMax),
	Math.ceil(pesoTotal/parametroValor["pesoMaximo"])));//+maxCodigoPallet;
}		
range numeroPallet = 1..maxPalletsPosibles;
/*
range numeroPalletNuevos = (1+maxCodigoPallet)..maxPalletsPosibles;
float maxPesoPallet[plt in numeroPallet] = 0;
float maxAltoPallet[plt in numeroPallet] = 0;
execute{	
	if (maxCodigoPallet>0){
		for (var pe in palletExtra){
				maxPesoPallet[pe.codigoPallet]=pe.pesoPermitido;
				maxAltoPallet[pe.codigoPallet]=pe.altoPermitido;
		}
	}
	for (var plt in numeroPalletNuevos){
				maxPesoPallet[plt]=parametroValor["pesoMaximo"];
				maxAltoPallet[plt]=AltoMax;
		}				
}
*/
float maxPalletJabas[ji in jabaInformacion] = 0;
execute{
for (var ji in jabaInformacion){
			maxPalletJabas[ji]=ji.demanda*Math.max(ji.alto/AltoMax,ji.peso/parametroValor["pesoMaximo"]);}}
execute{
	cplex.tilim = 60;
	//cplex.parallelmode = -1;
	//cplex.heurfreq = 1;
	cplex.epgap=.1;
	//cplex.workmem=6000;
	//cplex.lbheur=1;
}
//Begin
//Variables
dvar boolean usarPallet[numeroPallet];
dvar boolean esAsignadaJabaAPallet[jabas][numeroPallet];
dvar int+ cantidadJabaAsignadaPallet[jabas][numeroPallet];
/*
dvar float+ maxx[numeroPallet] in minimoX..maximoX;
dvar float+ maxy[numeroPallet] in minimoY..maximoY;
dvar float+ minx[numeroPallet] in minimoX..maximoX;
dvar float+ miny[numeroPallet] in minimoY..maximoY;
*/
//costo por envio de cada pallet, para maximizar la cantidad de jabas por pallet
dexpr float costoEnviado = parametroValor["costoEnvio"]*sum(plt in numeroPallet) usarPallet[plt];
//dexpr float costoDistancia = parametroValor["costoTransporte"]*sum(plt in numeroPallet)((maxx[plt]-minx[plt])+(maxy[plt]-miny[plt]));
dexpr float costoDistribucion=sum(ji in jabaInformacion) maxPalletJabas[ji]*(sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]);
//Objective
minimize costoEnviado+costoDistribucion;//+costoDistancia
//Constraints
subject to {
	//covertura de medidas por pallet
	forall (plt in numeroPallet){
		sum(ji in jabaInformacion) ji.peso*cantidadJabaAsignadaPallet[ji.jaba][plt]<=parametroValor["pesoMaximo"]*usarPallet[plt];
		sum(ji in jabaInformacion) ji.alto*cantidadJabaAsignadaPallet[ji.jaba][plt]<=AltoMax*usarPallet[plt];	
		/*
		miny[plt] <=maxy[plt];
		minx[plt] <=maxx[plt];
		*/
	}		
	//covertura de demanda por articulo
	forall(ji in jabaInformacion){
		sum(plt in numeroPallet) cantidadJabaAsignadaPallet[ji.jaba][plt]==ji.demanda;
		sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]>=1;
	}	
	forall(plt in numeroPallet, ji in jabaInformacion){
		//unicidad de variable 	cantidadJabaAsignadaPallet y esAsignadaJabaAPallet	
		cantidadJabaAsignadaPallet[ji.jaba][plt]<=esAsignadaJabaAPallet[ji.jaba][plt]*ji.demanda;
		cantidadJabaAsignadaPallet[ji.jaba][plt]>=esAsignadaJabaAPallet[ji.jaba][plt];
		esAsignadaJabaAPallet[ji.jaba][plt]<=usarPallet[plt];	
		/*	
		maxx[plt]>=minimoX+esAsignadaJabaAPallet[ji.jaba][plt]*(ji.x-minimoX);
		maxy[plt]>=minimoY+esAsignadaJabaAPallet[ji.jaba][plt]*(ji.y-minimoY);
		minx[plt]<=maximoX+esAsignadaJabaAPallet[ji.jaba][plt]*(ji.x-maximoX);
		miny[plt]<=maximoY+esAsignadaJabaAPallet[ji.jaba][plt]*(ji.y-maximoY);		
		*/
	}		
	//cycle-breaking constraints
	forall(plt in numeroPallet: plt > 1){
		usarPallet[plt-1] >= usarPallet[plt];
		}	
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
{jabasXPalletTipo} jabasNPallet = {<ji.jaba,ji.peso,ji.alto,cantidadJabaAsignadaPallet[ji.jaba][plt],plt,ji.x,ji.y> |plt in numeroPallet, ji in jabaInformacion:cantidadJabaAsignadaPallet[ji.jaba][plt]>= 0.9};
execute{writeln(jabasNPallet);}