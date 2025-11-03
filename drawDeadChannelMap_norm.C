#include "rapidjson/document.h"
#include "TH2F.h"
#include "TCanvas.h"
#include "CCDB/CcdbApi.h"
#include "TPCBase/DeadChannelMapCreator.h"
#include "TPCBase/Painter.h"
#include "TPCBase/Utils.h"
#include "TPCBase/Mapper.h"

using namespace o2::tpc;

void drawDeadChannelMap_norm(int run, bool drawAll = false, int maxEntries = -1)
{
  TH1::AddDirectory(false);

  o2::ccdb::CcdbApi api;
  api.init("http://alice-ccdb.cern.ch");

  const std::string path = fmt::format("TPC/Calib/IDC_PadStatusMap_A/runNumber={}", run);
  auto json = api.list(path.data(), false, "application/json");

  rapidjson::Document doc;
  doc.Parse(json.data());

  if (!doc.IsObject() || !doc.HasMember("objects") || !doc["objects"].IsArray()) {
    throw std::runtime_error(fmt::format("could not parse object list for {}", path));
  }

  auto entries = doc["objects"].GetArray();
  LOGP(info, "Found {} entries for object {}", entries.Size(), path);

  std::sort(entries.begin(), entries.end(), [](const auto& a, const auto& b) { return a["validFrom"].GetInt64() < b["validFrom"].GetInt64(); });

  DeadChannelMapCreator deadChannelMapCreator;
  deadChannelMapCreator.init(api.getURL());

  TObjArray arrCanvases;

  auto cDeadChannels = new TCanvas(fmt::format("cDeadChannels_run{}", run).data(), fmt::format("Dead Channels per Stack run {}", run).data(), 1200, 800);
  arrCanvases.Add(cDeadChannels);

  const int nEntries = maxEntries > 0 ? std::min(maxEntries, static_cast<int>(entries.Size())) : entries.Size();
  auto hDeadChannelsPerStack = new TH2F("hDeadChannelsPerSector", "Dead Channels per Stack;Entry;Stack (0-35: IROC, 36-71 OROC1, ...);#Dead Channels", nEntries, 0, nEntries, 144, 0, 144);

  int ientry = 0;
  for (const auto& entry : entries) {
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

    const std::vector<int> pads{Mapper::getPadsInOROC1(), Mapper::getPadsInOROC2(), Mapper::getPadsInOROC3()};

    for (size_t iRoc = 0; iRoc < map.getData().size(); ++iRoc) {
      auto& roc = map.getCalArray(iRoc);
      auto& data = roc.getData();
      if (iRoc < 36) {
        hDeadChannelsPerStack->Fill(ientry, iRoc, roc.getSum<float>() / static_cast<float>(Mapper::getPadsInIROC()));
      } else {
        const auto sumO1 = std::accumulate(data.begin(), data.begin() + pads[0], 0.f) / static_cast<float>(pads[0]);
        const auto sumO2 = std::accumulate(data.begin() + pads[0], data.begin() + pads[0] + pads[1], 0.f) / static_cast<float>(pads[1]);
        const auto sumO3 = std::accumulate(data.begin() + pads[0] + pads[1], data.end(), 0.f) / static_cast<float>(pads[2]);
        hDeadChannelsPerStack->Fill(ientry, iRoc, sumO1);
        hDeadChannelsPerStack->Fill(ientry, iRoc + 36, sumO2);
        hDeadChannelsPerStack->Fill(ientry, iRoc + 72, sumO3);
      }
    }

    auto canvas = painter::draw(map, 300, 0, 1);
    canvas->SetName(fmt::format("DeadChannelMap_{}_{:03}_{}_{}", run, ientry, startValidity, endValidity).data());
    canvas->SetTitle(fmt::format("Dead Channel Map for run {} ({}: {} - {})", run, ientry, startValidity, endValidity).data());
    arrCanvases.Add(canvas);
    ++ientry;
  }

  cDeadChannels->cd();
  hDeadChannelsPerStack->SetStats(false);
  hDeadChannelsPerStack->Draw("COLZ");
  o2::tpc::painter::adjustPalette(hDeadChannelsPerStack, 0.92);

  utils::saveCanvases(arrCanvases, "./", drawAll ? "png,png" : "", fmt::format("DeadChannelMap_run{}_norm.root", run).data());
  if (!drawAll) {
    cDeadChannels->SaveAs(fmt::format("DeadChannelMap_run{}_norm.png", run).data());
  }
}
