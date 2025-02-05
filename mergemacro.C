void mergemacro() {
    // 병합할 ROOT 파일들의 목록
    int start = 0;
    int end = 99;
    std::vector<std::string> fileNames;
    for(int i = start; i <= end; i++) {
        fileNames.push_back("AnalysisResults" + std::to_string(i) + ".root");
    }
    
    // 병합된 히스토그램을 저장할 새로운 ROOT 파일 생성
    TFile outputFile("merged_AnalysisResults.root", "RECREATE");

    // 첫 번째 파일을 열어 히스토그램 이름 리스트 추출
    TFile *firstFile = TFile::Open(fileNames[0].c_str());
    if (!firstFile || firstFile->IsZombie()) {
        std::cerr << "Error opening file " << fileNames[0] << std::endl;
    }

    // 파일 안에 있는 모든 히스토그램을 탐색
    TIter next(firstFile->GetListOfKeys());
    TKey *key;
    while ((key = (TKey*)next())) {
        // 히스토그램 타입인지 확인 (TH1F, TH1D, TH2D 포함)
        TString className = key->GetClassName();
        if (className != "TH1F" && className != "TH1D" && className != "TH2D")
            continue;
        
        std::string histName = key->GetName();  // 히스토그램 이름

        // 첫 번째 파일에서 히스토그램 가져오기
        TH1 *mergedHist = nullptr;
        if (className == "TH2D") {
            mergedHist = (TH2D*)firstFile->Get(histName.c_str());
        } else {
            mergedHist = (TH1*)firstFile->Get(histName.c_str());
        }
        
        if (!mergedHist) {
            std::cerr << "Error loading histogram " << histName << " from file " << fileNames[0] << std::endl;
            continue;
        }

        // 다른 파일에서 동일한 이름의 히스토그램들을 병합
        for (size_t i = 1; i < fileNames.size(); ++i) {
            TFile *file = TFile::Open(fileNames[i].c_str());
            if (!file || file->IsZombie()) {
                std::cerr << "Error opening file " << fileNames[i] << std::endl;
                continue;
            }

            // 해당 파일에서 히스토그램 가져오기
            TH1 *histToAdd = nullptr;
            if (className == "TH2D") {
                histToAdd = (TH2D*)file->Get(histName.c_str());
            } else {
                histToAdd = (TH1*)file->Get(histName.c_str());
            }
            
            if (histToAdd) {
                mergedHist->Add(histToAdd);  // 히스토그램 병합
            } else {
                std::cerr << "Histogram " << histName << " not found in file " << fileNames[i] << std::endl;
            }
            file->Close();
        }

        // 병합된 히스토그램을 새로운 파일에 저장
        outputFile.cd();
        mergedHist->Write();
    }

    // 첫 번째 파일 닫기
    firstFile->Close();

    // 최종 파일 닫기
    outputFile.Close();

}
