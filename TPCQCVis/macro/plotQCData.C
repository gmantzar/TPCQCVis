#if !defined(__CLING__) || defined(__ROOTCLING__)
#include <iostream>
#include <fmt/format.h>
#include "TFile.h"
#include "TCanvas.h"
#include <TH1.h>
#include <TH2.h>
#include <TH3.h>
#include "TLatex.h"
#include "TPCBase/Painter.h"
#include "TPCBase/CalDet.h"
#include "TPCBase/Utils.h"
#include "TPC/ClustersData.h"
#include "QualityControl/MonitorObject.h"
#include "CommonUtils/StringUtils.h"
#include "TTree.h"

#include <random>
#include "rapidjson/document.h"
#include "CCDB/CcdbApi.h"
#include "TPCBase/DeadChannelMapCreator.h"
#include "TPCBase/Mapper.h"

#endif

/// This can read a file containing Clusters, PID and Tracks
/// QC output as stored from MC productions.
/// Call the macro with root -b -q plotQCData.C+'("filename.root")'
/// The output will be a file called filename_QC.root containing all QC plots.

// Function to draw the 2D cluster histograms with R vs Phi vs Variable
std::vector<TH1*> drawRPhi(o2::tpc::CalDet<float> calDet, std::string name)
{
  std::vector<TH1*> outVec;
  std::vector<o2::tpc::CalDet<float>> vCalDet = {calDet};
  auto h3DCalDet = o2::tpc::painter::convertCalDetToTH3(vCalDet, true, 350, 80, 255, 360, 1);
  // A-Side
  h3DCalDet.GetZaxis()->SetRangeUser(0.,1.);
  auto h2D_CalDet_Aside = h3DCalDet.Project3D("yx");
  h2D_CalDet_Aside->SetName((string("h2DRPhi")+name.c_str()+string("Aside")).c_str());
  h2D_CalDet_Aside->SetTitle((name.c_str()+string(" (A-Side)")).c_str());
  h2D_CalDet_Aside->GetYaxis()->SetTitle("R (cm)");
  h2D_CalDet_Aside->GetXaxis()->SetTitle("Phi (rad)");
  outVec.push_back(h2D_CalDet_Aside);
  // C-Side
  h3DCalDet.GetZaxis()->SetRangeUser(-1.,0.);
  auto h2D_CalDet_Cside = h3DCalDet.Project3D("yx");
  h2D_CalDet_Cside->SetName((string("h2DRPhi")+name.c_str()+string("Cside")).c_str());
  h2D_CalDet_Cside->SetTitle((name.c_str()+string(" (C-Side)")).c_str());
  h2D_CalDet_Cside->GetYaxis()->SetTitle("R (cm)");
  h2D_CalDet_Cside->GetXaxis()->SetTitle("Phi (rad)");
  outVec.push_back(h2D_CalDet_Cside);
  return outVec;
}

bool isFilled(TFile *f)
{
  // Using tracks to check if plots are filled as this task is probably always included
  TObjArray* trArr;
  if (f->GetDirectory("int")) {
    trArr = (TObjArray*)f->Get("int/TPC/PID");
  }
  else if (f->GetDirectory("TPC")) {
    trArr = (TObjArray*)f->Get("TPC/PID");
  }
  else{
    trArr = (TObjArray*)f->Get("PID");
  }
  auto trMO = (o2::quality_control::core::MonitorObject*)trArr->At(0);
  auto hist = (TH1F*)trMO->getObject();
  if (hist->GetEntries() > 0) {
    return true;
  }
  else {
    return false;
  }
}
/*
bool hasMovingWindows(TFile *f)
{
  if (f->GetDirectory("mw")) {
    TObjArray* trArr;
    trArr = (TObjArray*)f->Get("mw/TPC/Tracks");
    auto trMO = (o2::quality_control::core::MonitorObject*)trArr->At(0);
    auto hist = (TH1F*)trMO->getObject();
    if (hist->GetEntries() > 0) {
      return true;
    }
  }
  return false;
}
*/

void plotQCData(const std::string filename)
{
  /// set up I/O
  TFile *f = new TFile(filename.c_str(), "read");
  auto name = o2::utils::Str::tokenize(filename, '.');

  // Check if TPC plots are filled
  if (isFilled(f) == false) {
    std::cout << "TPC not included in run" << std::endl;
    return;
  }

  TFile *fout = new TFile(fmt::format("{}_QC.root", name[0]).data(), "recreate");
   
//-------------------------------------------------
  /// Tracks QC
  TObjArray* trArr;
  if (f->GetDirectory("int")) {
    trArr = (TObjArray*)f->Get("int/TPC/Tracks");
  }
  else if (f->GetDirectory("TPC")) {
    trArr = (TObjArray*)f->Get("TPC/Tracks");
  }
  else{
    trArr = (TObjArray*)f->Get("Tracks");
  }

  if (trArr) {
    fout->cd();
    gDirectory->mkdir("TracksQC");
    fout->cd("TracksQC");
  
    for (int i = 0; i < trArr->GetEntries(); i++) {
      auto trMO = (o2::quality_control::core::MonitorObject*)trArr->At(i);
      auto hist = (TH1F*)trMO->getObject();
      hist->Write("",TObject::kOverwrite);
    }
  }
  
//-------------------------------------------------
  /// PID QC
  TObjArray* pidArr;
  if (f->GetDirectory("int")) {
    pidArr = (TObjArray*)f->Get("int/TPC/PID");
  }
  else if (f->GetDirectory("TPC")) {
    pidArr = (TObjArray*)f->Get("TPC/PID");
  }
  else{
    pidArr = (TObjArray*)f->Get("PID");
  }

  if (pidArr) {
    fout->cd();
    gDirectory->mkdir("PIDQC");
    fout->cd("PIDQC");
  
    for (int i = 0; i < pidArr->GetEntries(); i++) {
      auto pidMO = (o2::quality_control::core::MonitorObject*)pidArr->At(i);
      auto hist = (TH1F*)pidMO->getObject();
      hist->Write("",TObject::kOverwrite);
    }
  }

//-------------------------------------------------
  /// Track Clustesters QC
  TObjArray* trackClustersArr;
  if (f->GetDirectory("int")) {
    trackClustersArr = (TObjArray*)f->Get("int/TPC/TrackClusters");
  }
  else if (f->GetDirectory("TPC")) {
    trackClustersArr = (TObjArray*)f->Get("TPC/TrackClusters");
  }
  else{
    trackClustersArr = (TObjArray*)f->Get("TrackClusters");
  }

  if (trackClustersArr) {
    fout->cd();
    gDirectory->mkdir("TrackClustersQC");
    fout->cd("TrackClustersQC");
  
    for (int i = 0; i < trackClustersArr->GetEntries(); i++) {
      auto trackClustersMO = (o2::quality_control::core::MonitorObject*)trackClustersArr->At(i);
      auto hist = (TH1F*)trackClustersMO->getObject();
      hist->Write("",TObject::kOverwrite);
    }
  }
//-------------------------------------------------

/// Cluster QC
  TObjArray* clusArr;
  if (f->GetDirectory("int")) {
    clusArr = (TObjArray*)f->Get("int/TPC/Clusters");
  }
  else if (f->GetDirectory("TPC")) {
    clusArr = (TObjArray*)f->Get("TPC/Clusters");
  }
  else{
    clusArr = (TObjArray*)f->Get("Clusters");
  }

  if (clusArr) {
    auto mo = (o2::quality_control::core::MonitorObject*)clusArr->At(0);
    auto cl = (o2::quality_control_modules::tpc::ClustersData*)mo->getObject();

    fout->cd();
    gDirectory->mkdir("ClusterQC");
    fout->cd("ClusterQC");

    // R vs Phi TH2s
    if(true) {
      auto vh2DnClusters = drawRPhi(cl->getClusters().getNClusters(),"nClusters");
      vh2DnClusters[0]->Write("",TObject::kOverwrite);
      vh2DnClusters[1]->Write("",TObject::kOverwrite);
      auto vh2DqMax = drawRPhi(cl->getClusters().getQMax(),"qMax");
      vh2DqMax[0]->Write("",TObject::kOverwrite);
      vh2DqMax[1]->Write("",TObject::kOverwrite);
      auto vh2DqTot = drawRPhi(cl->getClusters().getQTot(),"qTot");
      vh2DqTot[0]->Write("",TObject::kOverwrite);
      vh2DqTot[1]->Write("",TObject::kOverwrite);
      auto vh2DSigmaTime = drawRPhi(cl->getClusters().getSigmaTime(),"SigmaTime");
      vh2DSigmaTime[0]->Write("",TObject::kOverwrite);
      vh2DSigmaTime[1]->Write("",TObject::kOverwrite);
      auto vh2DSigmaPad = drawRPhi(cl->getClusters().getSigmaPad(),"SigmaPad");
      vh2DSigmaPad[0]->Write("",TObject::kOverwrite);
      vh2DSigmaPad[1]->Write("",TObject::kOverwrite);
      auto vh2DTimeBin = drawRPhi(cl->getClusters().getTimeBin(),"TimeBin");
      vh2DTimeBin[0]->Write("",TObject::kOverwrite);
      vh2DTimeBin[1]->Write("",TObject::kOverwrite);
    }

    // Overview Canvases
    /// ----------------------------> YOU CAN SET THE HISTO RANGES HERE!! <-----------------------------
    auto nCl = o2::tpc::painter::makeSummaryCanvases(cl->getClusters().getNClusters(), 300, 0,cl->getClusters().getNClusters().getMean()*5);       // <-----
    auto qMax = o2::tpc::painter::makeSummaryCanvases(cl->getClusters().getQMax(), 300, 0, 200);              // <-----
    auto qTot = o2::tpc::painter::makeSummaryCanvases(cl->getClusters().getQTot(), 300, 0, 600);              // <-----
    auto sigmaTime = o2::tpc::painter::makeSummaryCanvases(cl->getClusters().getSigmaTime(), 300, 0, 1.); // <-----
    auto sigmaPad = o2::tpc::painter::makeSummaryCanvases(cl->getClusters().getSigmaPad(), 300, 0, 0.8);   // <-----
    auto timeBin = o2::tpc::painter::makeSummaryCanvases(cl->getClusters().getTimeBin(), 300, 6875, 7250);  // <-----
      
    nCl[0]->Write("",TObject::kOverwrite);
    nCl[1]->Write("",TObject::kOverwrite);
    nCl[2]->Write("",TObject::kOverwrite);
    qMax[0]->Write("",TObject::kOverwrite);
    qMax[1]->Write("",TObject::kOverwrite);
    qMax[2]->Write("",TObject::kOverwrite);
    qTot[0]->Write("",TObject::kOverwrite);
    qTot[1]->Write("",TObject::kOverwrite);
    qTot[2]->Write("",TObject::kOverwrite);
    sigmaTime[0]->Write("",TObject::kOverwrite);
    sigmaTime[1]->Write("",TObject::kOverwrite);
    sigmaTime[2]->Write("",TObject::kOverwrite);
    sigmaPad[0]->Write("",TObject::kOverwrite);
    sigmaPad[1]->Write("",TObject::kOverwrite);
    sigmaPad[2]->Write("",TObject::kOverwrite);
    timeBin[0]->Write("",TObject::kOverwrite);
    timeBin[1]->Write("",TObject::kOverwrite);
    timeBin[2]->Write("",TObject::kOverwrite);
  }

  //-------------------------------------------------
  /// Moving Windows QC
  /*
  if (hasMovingWindows(f)) {
    TObjArray* mwPidArr;
    TObjArray* mwTracksArr;
    if (f->GetDirectory("mw")) {
      mwPidArr = (TObjArray*)f->Get("mw/TPC/PID");
      mwTracksArr = (TObjArray*)f->Get("mw/TPC/Tracks");
    }
    fout->cd();
    gDirectory->mkdir("mw");
    fout->cd("mw");
    if (mwPidArr) {
      gDirectory->mkdir("PIDQC");
      fout->cd("PIDQC");
      for (int i = 0; i < pidArr->GetEntries(); i++) {
        auto pidMO = (o2::quality_control::core::MonitorObject*)pidArr->At(i);
        auto hist = (TH1F*)pidMO->getObject();
        hist->Write("",TObject::kOverwrite);
      }
    }
  }
*/
//-------------------------------------------------

  // Bethe-Bloch parameters tree
  TTree* betheTree = (TTree*)f->Get("BetheBlochParameters");
  if (betheTree) {
      fout->cd();
      TTree* clonedTree = betheTree->CloneTree();
      clonedTree->Write();
  }

//-------------------------------------------------

/// Dead Channel Map
  int maxEntries = -1;
  //int maxEntries = 5;
  bool drawAll = false;

  //std::cout<<(name)<<std::endl;
  //std::cout<<(name[0])<<std::endl;
  //auto run = name[0]; //(int)name[0];


    int run = -999;
      // Find last '/' in the string
    size_t pos = name[0].find_last_of('/');
    if (pos != std::string::npos && pos + 1 < name[0].size()) {
        std::string lastPart = name[0].substr(pos + 1);
        try {
            run = std::stoi(lastPart);
            std::cout << "Last integer: " << run << std::endl;
        } catch (const std::invalid_argument&) {
            std::cout << "No valid integer found at the end." << std::endl;
        }
    } else {
        std::cout << "No '/' found in the string." << std::endl;
    }
  
  
  
  TH1::AddDirectory(false);

  o2::ccdb::CcdbApi api;
  api.init("http://alice-ccdb.cern.ch");

  const std::string path = fmt::format("TPC/Calib/IDC_PadStatusMap_A/runNumber={}", run);
  std::cout << "Fetching dead channel maps from CCDB path: " << path << std::endl;

  auto json = api.list(path.data(), false, "application/json");

  rapidjson::Document doc;
  doc.Parse(json.data());

  if (!doc.IsObject() || !doc.HasMember("objects") || !doc["objects"].IsArray()) {
    throw std::runtime_error(fmt::format("could not parse object list for {}", path));
  }

  auto entries = doc["objects"].GetArray();
  LOGP(info, "Found {} entries for object {}", entries.Size(), path);

  std::sort(entries.begin(), entries.end(), [](const auto& a, const auto& b) { return a["validFrom"].GetInt64() < b["validFrom"].GetInt64(); });

  o2::tpc::DeadChannelMapCreator deadChannelMapCreator;
  deadChannelMapCreator.init(api.getURL());

  TObjArray arrCanvases;

  auto cDeadChannels = new TCanvas(fmt::format("cDeadChannels_run{}", run).data(), fmt::format("Dead Channels per Stack run {}", run).data(), 1200, 800);
  arrCanvases.Add(cDeadChannels);

  const int nSample = 20;
  const int nEntries = maxEntries > 0 ? std::min(maxEntries, static_cast<int>(entries.Size())) : entries.Size();
  //auto hDeadChannelsPerStack = new TH2F("hDeadChannelsPerSector", "Dead Channels per Stack;Entry;Stack (0-35: IROC, 36-71 OROC1, ...);#Dead Channels", nEntries, 0, nEntries, 144, 0, 144);
  auto hDeadChannelsPerStack = new TH2F("hDeadChannelsPerSector", "Dead Channels per Stack;Entry;Stack (0-35: IROC, 36-71 OROC1, ...);#Dead Channels", nSample, 0, nSample, 144, 0, 144);

  int ientry = 0;
  // Deterministically sample 20 random entries from 'entries'
  std::vector<size_t> sampled_indices;
  std::mt19937 rng(42); // fixed seed for determinism
  std::vector<size_t> all_indices(entries.Size());
  std::iota(all_indices.begin(), all_indices.end(), 0);
  if (entries.Size() > nSample) {
    std::shuffle(all_indices.begin(), all_indices.end(), rng);
    sampled_indices.assign(all_indices.begin(), all_indices.begin() + nSample);
    std::sort(sampled_indices.begin(), sampled_indices.end());
  } else {
    for (size_t i = 0; i < entries.Size(); ++i) sampled_indices.push_back(i);
  }

  for (size_t sampled_idx : sampled_indices) {


    const auto& entry = entries[sampled_idx];
    if (maxEntries > 0 && ientry >= maxEntries) {
      LOGP(info, "Reached max entries limit: {}, stopping processing", maxEntries);
      break;
    }
    const auto startValidity = entry["validFrom"].GetInt64();
    const auto endValidity = entry["validUntil"].GetInt64();
    const auto timeStamp = (startValidity + endValidity) / 2;
    // std::string etag;
    // if (entry.FindMember("id") != entry.MemberEnd()) {
    //   etag = entry["id"].GetString();
    // }

    if (ientry % 100 == 0) {
      LOGP(info, "Processing entry {}/{} for run {}: {} - {}", ientry, entries.Size(), run, startValidity, endValidity);
    }

    deadChannelMapCreator.load(timeStamp);
    auto& map = deadChannelMapCreator.getDeadChannelMap();

    const std::vector<int> pads{o2::tpc::Mapper::getPadsInOROC1(), o2::tpc::Mapper::getPadsInOROC2(), o2::tpc::Mapper::getPadsInOROC3()};

    for (size_t iRoc = 0; iRoc < map.getData().size(); ++iRoc) {
      auto& roc = map.getCalArray(iRoc);
      auto& data = roc.getData();
      if (iRoc < 36) {
        hDeadChannelsPerStack->Fill(ientry, iRoc, roc.getSum<float>() / static_cast<float>(o2::tpc::Mapper::getPadsInIROC()));
      } else {
        const auto sumO1 = std::accumulate(data.begin(), data.begin() + pads[0], 0.f) / static_cast<float>(pads[0]);
        const auto sumO2 = std::accumulate(data.begin() + pads[0], data.begin() + pads[0] + pads[1], 0.f) / static_cast<float>(pads[1]);
        const auto sumO3 = std::accumulate(data.begin() + pads[0] + pads[1], data.end(), 0.f) / static_cast<float>(pads[2]);
        hDeadChannelsPerStack->Fill(ientry, iRoc, sumO1);
        hDeadChannelsPerStack->Fill(ientry, iRoc + 36, sumO2);
        hDeadChannelsPerStack->Fill(ientry, iRoc + 72, sumO3);
      }
    }

    auto canvas = o2::tpc::painter::draw(map, 300, 0, 1);
    canvas->SetName(fmt::format("DeadChannelMap_{}_{:03}_{}_{}", run, ientry, startValidity, endValidity).data());
    canvas->SetTitle(fmt::format("Dead Channel Map for run {} ({}: {} - {})", run, ientry, startValidity, endValidity).data());
    arrCanvases.Add(canvas);
    ++ientry;
  }

  cDeadChannels->cd();
  hDeadChannelsPerStack->SetStats(false);
  hDeadChannelsPerStack->Draw("COLZ");
  o2::tpc::painter::adjustPalette(hDeadChannelsPerStack, 0.92);

  fout->cd();
  gDirectory->mkdir("DeadChannelMapsTranding");
  fout->cd("DeadChannelMapsTranding");
  //arrCanvases.Write();
  hDeadChannelsPerStack->Write("hDeadChannelMaps");
  
  //utils::saveCanvases(arrCanvases, "./", drawAll ? "png,png" : "", fmt::format("DeadChannelMap_run{}_norm.root", run).data());
  //if (!drawAll) {
  //  cDeadChannels->SaveAs(fmt::format("DeadChannelMap_run{}_norm.png", run).data());
  //}


  fout->Close();
  return;
}