void mergetuple() {
    // 사용자가 정의한 파일 숫자 시작과 끝
    int start = 0;
    int end = 99;

    // Create a new ROOT file to store the merged data
    TFile *mergedFile = new TFile("merged_tuple.root", "RECREATE");
    TNtuple *mergedNtuple = new TNtuple("mergedNtuple", "Merged Dijet Ntuple", "eventNum:dijetMass:leadingJetPt:subleadingJetPt:deltaPhi:deltaEta:x1:x2:parton1Id:parton2Id");

    // Define variables to hold data
    float eventNum, dijetMass, leadingJetPt, subleadingJetPt, deltaPhi, deltaEta, x1, x2, parton1Id, parton2Id;

    // Loop through files from start to end
    for (int i = start; i <= end; i++) {
        TString fileName = TString::Format("AnalysisResults%d.root", i);
        TFile *file = new TFile(fileName, "READ");
        TNtuple *dijetNtuple = (TNtuple*)file->Get("dijetNtuple");

        // Set branch addresses
        dijetNtuple->SetBranchAddress("eventNum", &eventNum);
        dijetNtuple->SetBranchAddress("dijetMass", &dijetMass);
        dijetNtuple->SetBranchAddress("leadingJetPt", &leadingJetPt);
        dijetNtuple->SetBranchAddress("subleadingJetPt", &subleadingJetPt);
        dijetNtuple->SetBranchAddress("deltaPhi", &deltaPhi);
        dijetNtuple->SetBranchAddress("deltaEta", &deltaEta);
        dijetNtuple->SetBranchAddress("x1", &x1);
        dijetNtuple->SetBranchAddress("x2", &x2);
        dijetNtuple->SetBranchAddress("parton1Id", &parton1Id);
        dijetNtuple->SetBranchAddress("parton2Id", &parton2Id);

        // Fill the merged ntuple
        Long64_t nentries = dijetNtuple->GetEntries();
        for (Long64_t j = 0; j < nentries; j++) {
            dijetNtuple->GetEntry(j);
            mergedNtuple->Fill(eventNum, dijetMass, leadingJetPt, subleadingJetPt, deltaPhi, deltaEta, x1, x2, parton1Id, parton2Id);
        }

        file->Close();
    }

    // Write the merged ntuple to the new file
    mergedFile->cd();
    mergedNtuple->Write();

    // Close the merged file
    mergedFile->Close();
}
