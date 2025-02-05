#include <iostream>
#include <TFile.h>
#include <TTree.h>
#include <TF1.h>
#include <TH1.h>
#include <TRandom.h>
#include <TClonesArray.h>
#include <Pythia8/Pythia.h>
// #include <Pythia8/HeavyIons.h>
#include <TStopwatch.h>
#include <TAxis.h>
#include <THnSparse.h>
#include <THashList.h>
#include <TString.h>
#include <TLorentzVector.h>
#include <TVector2.h>
#include <TRandom3.h>
#include <TH2D.h>
#include <TNtuple.h>

#include "fastjet/config.h"
#include "fastjet/PseudoJet.hh"
#include "fastjet/JetDefinition.hh"
#include "fastjet/ClusterSequenceArea.hh"
#include "fastjet/AreaDefinition.hh"
#include "fastjet/tools/JetMedianBackgroundEstimator.hh"

using namespace std;
using namespace fastjet;
using namespace Pythia8;
TFile *fOutput;

int main(int argc, char **argv)
{

	Int_t randomseed = atoi(argv[1]); //placing the inputs into variables
	char *outFile = argv[2];

	fOutput = new TFile(outFile, "recreate");

	//---------------------
	//Pythia initialization
	//---------------------

	Pythia pythia; // Generator.


	pythia.readFile("pythia_config.cmnd"); 
	int nEvent = pythia.mode("Main:numberOfEvents");
	pythia.readString("Random:setSeed = on");
	pythia.readString(Form("Random:seed=%d", randomseed));
	pythia.readString("111:mayDecay = on");

	pythia.init();

	TStopwatch timer;
	timer.Start();

	Double_t bindijetmass[] = {40, 45, 55, 65, 75, 85, 100, 115, 130, 150};//charged jet
	Double_t nbindijetmass = sizeof(bindijetmass)/sizeof(bindijetmass[0])-1;
	auto hnevent = new TH1D ("hnevent","hnevent", 1, 0,1);
	auto hDijetMass = new TH1D ("hDijetMass","hDijetMass; M_{ij} (GeV/c^2); Event;", nbindijetmass, bindijetmass);

	int nBins = 100; 
    double min = 10e-7; 
    double max = 1; 

    double binEdges[nBins + 1];
    double logMin = TMath::Log10(min);
    double logMax = TMath::Log10(max);

    for (int i = 0; i <= nBins; ++i) {
        binEdges[i] = TMath::Power(10, logMin + i * (logMax - logMin) / nBins);
    }

	auto hPartonicX = new TH2D ("hPartonicX","Partonic x distribution;x_{1};x_{2}", nBins, binEdges, nBins, binEdges);

	// Create TNtuple to store dijet information
	TNtuple *dijetNtuple = new TNtuple("dijetNtuple", "Dijet Information", 
		"eventNum:dijetMass:leadingJetPt:subleadingJetPt:deltaPhi:deltaEta:x1:x2:parton1Id:parton2Id");

	double const jetradius = 0.4; // R resolution parameter

	//event loop
	vector<fastjet::PseudoJet> particlesforjets;

	for (int ievt = 0; ievt < nEvent; ievt++)
	{	
		Double_t sigma = pythia.info.sigmaGen();
		if (!pythia.next()) continue;
		hnevent->Fill(0.5);
		if (ievt % 10000 == 0) cout << ievt << endl;

		particlesforjets.clear();
		fastjet::PseudoJet fTrack;

		for (int i = 0; i < pythia.event.size(); i++)
		{ //loop over all the particles in the event
			Particle &p = pythia.event[i];
			if (!p.isFinal() || fabs(p.eta()) > 0.9 || !p.isCharged() || p.pT() < 0.15) continue;
			fTrack = fastjet::PseudoJet(p.px(), p.py(), p.pz(), p.e());
			particlesforjets.push_back(fTrack);
		}

		vector<fastjet::PseudoJet> jets;
		fastjet::JetDefinition jet_def(fastjet::antikt_algorithm, jetradius, fastjet::pt_scheme);
		fastjet::ClusterSequence cs(particlesforjets, jet_def);
		jets = fastjet::sorted_by_pt(cs.inclusive_jets(20)); // APPLY Min pt cut for jet
		
		vector<fastjet::PseudoJet> jets_eta_cut;
		for (const auto& jet : jets) 
		{
			if (fabs(jet.eta()) < 0.5)
			{
				jets_eta_cut.push_back(jet);
			}
		}

		if (jets_eta_cut.size() < 2) continue;
		
		fastjet::PseudoJet leading_jet = jets_eta_cut[0];

		bool found_pair = false;
		for (auto i = 1; i < jets_eta_cut.size() && !found_pair; i++) 
		{
			fastjet::PseudoJet subleading_jet = jets_eta_cut[i];
			Double_t dphi = fabs(leading_jet.phi() - subleading_jet.phi());
			Double_t deta = leading_jet.eta() - subleading_jet.eta();
			Double_t condition = fabs(dphi - M_PI);
			
			if (condition < (M_PI/2.0)) {
				Double_t dijet_mass = sqrt(2*leading_jet.pt()*subleading_jet.pt()*(cosh(deta)-cos(dphi)));
				hDijetMass->Fill(dijet_mass,sigma);
				
				// Get partonic information
				double x1 = pythia.info.x1();
				double x2 = pythia.info.x2();
				int id1 = pythia.info.id1();
				int id2 = pythia.info.id2();
				
				hPartonicX->Fill(x1, x2);

				// Fill ntuple with event information
				float ntuple_data[10] = {
					(float)ievt,              // event number
					(float)dijet_mass,        // dijet mass
					(float)leading_jet.pt(),  // leading jet pt
					(float)subleading_jet.pt(), // subleading jet pt
					(float)dphi,              // delta phi
					(float)deta,              // delta eta
					(float)x1,                // x1 of parton
					(float)x2,                // x2 of parton
					(float)id1,               // parton 1 ID
					(float)id2                // parton 2 ID
				};
				
				dijetNtuple->Fill(ntuple_data);
				found_pair = true;
			}
		}
	} // event loop done.
	pythia.stat();
	
	hnevent->Write();	
	hDijetMass->Write();
	hPartonicX->Write();
	dijetNtuple->Write();
	
	fOutput->Close();
	timer.Print();
}
