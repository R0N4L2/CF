/*********************************************
 * OPL 12.8.0.0 Model
 * Author: ronal
 * Creation Date: 3-10-2019 at 10:32:04
 *********************************************/


int palletsDisponibles=...;
float palletVolumen=...;
float palletLargo=...;
float palletAncho=...;
float palletALto=...;
float palletPeso=...;
float palletCosto=...;
float PenalidadNoEnviar=...;
float M=...;

tuple jabaInformacionTipo {
	string jaba;
	float peso;
	float volumen;	
	//float largo;
	//float ancho;
	float alto;
}
{jabaInformacionTipo} jabaInformacion = ...;
{string} jabas = {ji.jaba | ji in jabaInformacion};
float volumenTotal = sum(ji in jabaInformacion) ji.volumen;
float pesoTotal = sum(ji in jabaInformacion) ji.peso;
//float minLargo = min(ji in jabaInformacion) ji.largo;
//float minAncho = min(ji in jabaInformacion) ji.ancho;
float minAlto = min(ji in jabaInformacion) ji.alto;


int maxPalletsPosibles = 0;
execute{
	maxPalletsPosibles = Math.min(palletsDisponibles,Math.max((1 + Math.floor(volumenTotal / palletVolumen)),(1 + Math.floor(pesoTotal / palletPeso))));
	}

range numeroPallet = 1..maxPalletsPosibles;

execute{
	cplex.tilim = 600;
	cplex.parallelmode = -1;
	cplex.heurfreq = 1;
}


//Begin
//Variables
dvar boolean usarPallet[numeroPallet];
dvar float+ palletVolumenEnviado[plt in numeroPallet] in 0..palletVolumen;
dvar float+ palletPesoEnviado[plt in numeroPallet] in 0..palletPeso;
//dvar float+ x[jabas] in 0..(palletLargo-minLargo);
//dvar float+ y[jabas] in 0..(palletAncho-minAncho);
dvar float+ z[jabas] in 0..(palletALto-minAlto);
//dvar boolean lx[jabas];
//dvar boolean ly[jabas];
//dvar boolean ax[jabas];
//dvar boolean ay[jabas];
dvar boolean h[jabas];
//dvar boolean der[jabas][jabas];
//dvar boolean atras[jabas][jabas];
dvar boolean arriba[jabas][jabas];
dvar boolean esAsignadaJabaAPallet[jabas][numeroPallet];
dvar float+ volumenSinEnviar;
dexpr float costoEnviado = sum(plt in numeroPallet) palletCosto * usarPallet[plt];
dexpr float costoNoEnviado = PenalidadNoEnviar * volumenSinEnviar; 

//Objective
minimize
	costoEnviado + costoNoEnviado;	
//Constraints
subject to {
	sum(plt in numeroPallet) palletVolumenEnviado[plt] + volumenSinEnviar == volumenTotal;
	sum(plt in numeroPallet) usarPallet[plt] >=1;
	sum(plt in numeroPallet, ji in jabaInformacion) esAsignadaJabaAPallet[ji.jaba][plt]<=palletsDisponibles;
	sum(plt in numeroPallet) usarPallet[plt]<=palletsDisponibles;
	forall (plt in numeroPallet){
		sum(ji in jabaInformacion) ji.volumen * esAsignadaJabaAPallet[ji.jaba][plt] == palletVolumenEnviado[plt];
		sum(ji in jabaInformacion) ji.peso * esAsignadaJabaAPallet[ji.jaba][plt] == palletPesoEnviado[plt];
		sum(ji in jabaInformacion) esAsignadaJabaAPallet[ji.jaba][plt] >= usarPallet[plt];
		palletVolumenEnviado[plt] <= palletVolumen * usarPallet[plt];
		palletPesoEnviado[plt] <= palletPeso * usarPallet[plt];
	}		
	forall(ji1 in jabaInformacion,ji2 in jabaInformacion){
		//x[ji1.jaba]+ji1.largo*lx[ji1.jaba]+ji1.largo*ax[ji1.jaba] <= x[ji2.jaba]+(1-der[ji1.jaba][ji2.jaba])*M;
		//y[ji1.jaba]+ji1.largo*ly[ji1.jaba]+ji1.ancho*ay[ji1.jaba] <= y[ji2.jaba]+(1-atras[ji1.jaba][ji2.jaba])*M;
		z[ji1.jaba]+ji1.alto*h[ji1.jaba] <=z[ji2.jaba]+(1-arriba[ji1.jaba][ji2.jaba])*M;	
	}
	//forall(plt in numeroPallet,ji1 in jabaInformacion,ji2 in jabaInformacion: ji1.jaba!=ji2.jaba){
	//  der[ji1.jaba][ji2.jaba]+der[ji2.jaba][ji1.jaba]+atras[ji1.jaba][ji2.jaba]+atras[ji2.jaba][ji1.jaba]+arriba[ji1.jaba][ji2.jaba]+arriba[ji2.jaba][ji1.jaba]
	//  >= esAsignadaJabaAPallet[ji1.jaba][plt]+esAsignadaJabaAPallet[ji2.jaba][plt]-1;
	//}		
	forall(ji in jabaInformacion){
		arriba[ji.jaba][ji.jaba]==0;	
		//der[ji.jaba][ji.jaba]+atras[ji.jaba][ji.jaba]+arriba[ji.jaba][ji.jaba]==0;		
		//sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]==lx[ji.jaba]+ax[ji.jaba];
 		//sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]==ly[ji.jaba]+ay[ji.jaba];
 		//sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]==lx[ji.jaba]+ly[ji.jaba];
 		//sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]==ax[ji.jaba]+ay[ji.jaba];
 		sum(plt in numeroPallet) esAsignadaJabaAPallet[ji.jaba][plt]==h[ji.jaba];
		//x[ji.jaba]+ji.largo*lx[ji.jaba]+ji.ancho*ax[ji.jaba] <= sum(plt in numeroPallet) usarPallet[plt]*palletLargo;
		//y[ji.jaba]+ji.largo*ly[ji.jaba]+ji.ancho*ay[ji.jaba] <= sum(plt in numeroPallet) usarPallet[plt]*palletAncho;
		z[ji.jaba]+ji.alto*h[ji.jaba] <=sum(plt in numeroPallet) usarPallet[plt]*palletALto;	
	}			
}
//End
tuple jabaPalletTypeNumCantTipo{
	string jaba;
	int palletNumber;
	//float posx;
	//float posy;
	float posz;
	//float largo;
	//float ancho;
	float alto;
	float volumen;
	float peso;
}
//{jabaPalletTypeNumCantTipo} jabaAPalletCantidad = {<ji.jaba,plt,x[ji.jaba],y[ji.jaba],z[ji.jaba],ji.largo,ji.ancho,ji.alto,ji.volumen,ji.peso> | plt in numeroPallet, ji in jabaInformacion: esAsignadaJabaAPallet[ji.jaba][plt] >= 0.9};
{jabaPalletTypeNumCantTipo} jabaAPalletCantidad = {<ji.jaba,plt,z[ji.jaba],ji.alto,ji.volumen,ji.peso> | plt in numeroPallet, ji in jabaInformacion: esAsignadaJabaAPallet[ji.jaba][plt] >= 0.9};
execute{writeln(jabaAPalletCantidad);}
tuple PalletCantidadTipo{
	int palletNumber;
	float palletPesoEnviado;
	float palletVolumenEnviado;
}
{PalletCantidadTipo} PalletInfo = {<plt,palletPesoEnviado[plt],palletVolumenEnviado[plt]> | plt in numeroPallet: usarPallet[plt] >= 0.9};
execute{writeln(PalletInfo);}