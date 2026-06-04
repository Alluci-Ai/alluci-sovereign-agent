import SwiftUI

struct WalletView: View {
    @State private var activeTab = 0 // 0: Send, 1: Receive, 2: Convert
    @State private var activeChain = "VRSC"
    
    let chains = ["VRSC", "vETH", "DAI.vETH", "MKR.vETH", "Bridge.vETH"]
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                
                // Linked Fiat Card (Apple Wallet Style)
                ZStack {
                    RoundedRectangle(cornerRadius: 16)
                        .fill(LinearGradient(gradient: Gradient(colors: [Color.black, Color.gray.opacity(0.8)]), startPoint: .topLeading, endPoint: .bottomTrailing))
                    
                    VStack(alignment: .leading) {
                        HStack {
                            Image(systemName: "building.columns.fill").foregroundColor(.white)
                            Text("Linked Fiat Account").font(.subheadline).bold().foregroundColor(.white)
                            Spacer()
                            Image(systemName: "applelogo").foregroundColor(.white)
                        }
                        Spacer()
                        Text("JPMorgan Chase").font(.title2).bold().foregroundColor(.white)
                        Text("**** **** **** 4829").font(.caption).foregroundColor(.white.opacity(0.8))
                    }
                    .padding()
                }
                .frame(height: 120)
                .padding(.horizontal)
                
                // Multi-Chain Selector
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        ForEach(chains, id: \.self) { chain in
                            Button(action: { activeChain = chain }) {
                                Text(chain)
                                    .font(.caption).bold()
                                    .padding(.horizontal, 12).padding(.vertical, 6)
                                    .background(activeChain == chain ? Color.blue.opacity(0.2) : Color.gray.opacity(0.1))
                                    .foregroundColor(activeChain == chain ? .blue : .primary)
                                    .cornerRadius(8)
                            }
                        }
                    }
                    .padding(.horizontal)
                }
                
                // Dynamic Balance Tile
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("ACTIVE BALANCE").font(.caption).bold().foregroundColor(.secondary)
                        Spacer()
                        Image(systemName: "dollarsign.circle.fill").foregroundColor(.blue)
                    }
                    HStack(alignment: .firstTextBaseline) {
                        Text("$14,024.50").font(.system(size: 34, weight: .bold))
                        Text(activeChain).font(.headline).foregroundColor(.blue)
                    }
                    Text("● System Verified").font(.caption).foregroundColor(.green)
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .cornerRadius(12)
                .padding(.horizontal)
                
                // Identity Manifest & L1 Assets
                HStack(spacing: 16) {
                    VStack(alignment: .leading) {
                        Image(systemName: "shield.checkerboard").foregroundColor(.blue).padding(.bottom, 4)
                        Text("IDENTITY").font(.caption2).foregroundColor(.secondary)
                        Text("AlluciNode").font(.headline)
                        Text("alluci@").font(.caption).foregroundColor(.secondary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(12)
                    
                    VStack(alignment: .leading) {
                        Image(systemName: "server.rack").foregroundColor(.purple).padding(.bottom, 4)
                        Text("RESERVES").font(.caption2).foregroundColor(.secondary)
                        Text("vETH").font(.subheadline)
                        Text("DAI.vETH").font(.caption).foregroundColor(.secondary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(12)
                }
                .padding(.horizontal)
                
                // Consensus & Yield
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "waveform.path.ecg").foregroundColor(.green)
                        Text("CONSENSUS YIELD").font(.caption).bold()
                        Spacer()
                        Text("14.5% APY").font(.caption).bold().foregroundColor(.green)
                    }
                    HStack {
                        VStack(alignment: .leading) {
                            Text("Total Staked").font(.caption2).foregroundColor(.secondary)
                            Text("2,450.00").font(.subheadline).bold()
                        }
                        Spacer()
                        VStack(alignment: .trailing) {
                            Text("Network Hashrate").font(.caption2).foregroundColor(.secondary)
                            Text("845 GH/s").font(.subheadline).bold()
                        }
                    }
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .cornerRadius(12)
                .padding(.horizontal)
                
                // PBaaS Send/Receive/Convert Panel
                VStack {
                    Picker("PBaaS Action", selection: $activeTab) {
                        Text("Send").tag(0)
                        Text("Invoice").tag(1)
                        Text("Convert").tag(2)
                    }
                    .pickerStyle(SegmentedPickerStyle())
                    .padding()
                    
                    if activeTab == 0 {
                        VStack(alignment: .leading, spacing: 12) {
                            TextField("Recipient (R-address, i-address, VerusID@)", text: .constant(""))
                                .textFieldStyle(RoundedBorderTextFieldStyle())
                            HStack {
                                TextField("Amount", text: .constant(""))
                                    .textFieldStyle(RoundedBorderTextFieldStyle())
                                Text(activeChain).bold()
                            }
                            Button("Execute Transfer") {}
                                .buttonStyle(.borderedProminent)
                                .frame(maxWidth: .infinity)
                        }
                        .padding(.horizontal)
                    } else if activeTab == 1 {
                        VStack {
                            Image(systemName: "qrcode")
                                .resizable()
                                .frame(width: 150, height: 150)
                                .padding()
                            Text("VerusPay Invoice ready.").font(.caption).foregroundColor(.secondary)
                        }
                    } else {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("PBaaS Automated Market Maker").font(.caption).bold().foregroundColor(.purple)
                            HStack {
                                TextField("Amount", text: .constant(""))
                                    .textFieldStyle(RoundedBorderTextFieldStyle())
                                Text("VRSC").bold()
                            }
                            HStack {
                                Text("To:").foregroundColor(.secondary)
                                Spacer()
                                Text("vETH").bold().foregroundColor(.purple)
                            }
                            Button("Finalize Conversion") {}
                                .buttonStyle(.borderedProminent)
                                .tint(.purple)
                                .frame(maxWidth: .infinity)
                        }
                        .padding(.horizontal)
                    }
                }
                .padding(.bottom, 40)
            }
            .padding(.top)
        }
        .navigationTitle("Sovereign Wallet")
    }
}
