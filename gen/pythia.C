#include <iostream>
#include <memory>            
#include <TFile.h>
#include <TH1.h>
#include <TStopwatch.h>

#include <Pythia8/Pythia.h>
#include "fastjet/config.h"
#include "fastjet/PseudoJet.hh"
#include "fastjet/JetDefinition.hh"
#include "fastjet/ClusterSequence.hh"

using namespace std;
using namespace fastjet;
using namespace Pythia8;

int main(int argc, char **argv)
{
    int randomseed = atoi(argv[1]);
    const char *outFile = argv[2];
    const char *configFile = argv[3];

    std::unique_ptr<TFile> fOutput(new TFile(outFile, "recreate"));

    Pythia pythia;
    pythia.readFile(configFile);
    int nEvent = pythia.mode("Main:numberOfEvents");
    pythia.readString("Random:setSeed = on");
    pythia.readString(Form("Random:seed=%d", randomseed));
    pythia.init();

    const double pTHatMax = pythia.settings.parm("PhaseSpace:pTHatMax");
    const double jetPtCut = (pTHatMax > 0.0) ? 3.0 * pTHatMax : -1.0;

    TStopwatch timer;
    timer.Start();

    TH1D *hnevent = new TH1D("hnevent", "Number of events", 1, 0, 1);
    hnevent->SetDirectory(0);

    TH1D *hJetPt = new TH1D("hJetPt", "Jet p_{T}; p_{T} [GeV/c]; Counts", 200, 0, 200);
    hJetPt->SetDirectory(0);

    TH1D *hTrackPt = new TH1D("hTrackPt", "Charged track p_{T} (|#eta|<0.9); p_{T} [GeV/c]; Counts", 50, 0, 50);
    hTrackPt->SetDirectory(0);

    double const jetradius = 0.4; 
    vector<PseudoJet> particlesforjets;

    for (int ievt = 0; ievt < nEvent; ievt++)
    {
        if (!pythia.next()) continue;

        // Count all generated events
        hnevent->Fill(0.5);
        particlesforjets.clear();

        for (int i = 0; i < pythia.event.size(); i++)
        { 
            Particle &p = pythia.event[i];
            if (!p.isFinal() || fabs(p.eta()) > 0.9 || !p.isCharged() || p.pT() < 0.15) continue;

            // Fill charged-track pT histogram (disabled per request)
            hTrackPt->Fill(p.pT());

            // Use charged tracks as inputs to jet finding
            PseudoJet fTrack(p.px(), p.py(), p.pz(), p.e());
            particlesforjets.push_back(fTrack);
        }

        // Build anti-kT jets and fill jet pT
        JetDefinition jet_def(antikt_algorithm, jetradius); // default recombination scheme
        ClusterSequence cs(particlesforjets, jet_def);
        vector<PseudoJet> jets = sorted_by_pt(cs.inclusive_jets(0));
        for (const auto& jet : jets) {
            if (fabs(jet.eta()) < 0.5) {
                if (jetPtCut > 0.0 && jet.pt() > jetPtCut) continue; // Skip jets beyond configured hard scale
                hJetPt->Fill(jet.pt());
            }
        }
    }

    pythia.stat();

    // Store generated cross section (mb) in a 1-bin histogram
    TH1D *hSigmaGen = new TH1D("hSigmaGen", "#sigma_{gen} [mb];dummy;xsec", 1, 0, 1);
    hSigmaGen->SetDirectory(0);
    const double sigmaGen = pythia.info.sigmaGen();
    hSigmaGen->SetBinContent(1, sigmaGen);

    cout << "sigmaGen: " << sigmaGen << " mb" << endl;

    hnevent->Write();
    hJetPt->Write();
    hTrackPt->Write();
    hSigmaGen->Write();

    delete hnevent;
    delete hJetPt;
    delete hTrackPt;
    delete hSigmaGen;

    fOutput->Close();
    timer.Print();

    return 0;
}
