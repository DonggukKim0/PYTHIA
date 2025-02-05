void drawTuple()
{
    TFile *f = new TFile("merged_tuple.root", "READ");
    TNtuple *dijetNtuple = (TNtuple*)f->Get("mergedNtuple");

    float eventNum, dijetMass, leadingJetPt, subleadingJetPt, deltaPhi, deltaEta, x1, x2, parton1Id, parton2Id;
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

    Long64_t nentries = dijetNtuple->GetEntries();
    cout << "Total number of entries: " << nentries << endl;
    
    // Open CSV file for writing
    ofstream csvFile("dijet_data.csv");
    
    // Write CSV header
    csvFile << "Event,Mass,LeadPt,SubleadPt,DeltaPhi,DeltaEta,x1,x2,Parton1,Parton2" << endl;

    // Write data to CSV
    for (Long64_t i = 0; i < nentries; i++) {
        dijetNtuple->GetEntry(i);
        csvFile << fixed << setprecision(2);
        csvFile << (int)eventNum << ","
               << dijetMass << ","
               << leadingJetPt << ","
               << subleadingJetPt << ","
               << deltaPhi << ","
               << deltaEta << ","
               << x1 << ","
               << x2 << ","
               << (int)parton1Id << ","
               << (int)parton2Id << endl;
    }

    csvFile.close();
    f->Close();
    
    cout << "Data has been saved to dijet_data.csv" << endl;
}