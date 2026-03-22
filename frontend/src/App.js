import { useEffect, useState } from "react";

const API = process.env.REACT_APP_API_URL;

function App() {
  const [teamsSet, setTeamsSet] = useState(false);
  const [offense, setOffense] = useState("");
  const [defense, setDefense] = useState("");

  const [form, setForm] = useState({
    down: 1,
    ydstogo: 10,
    yardline_100: 50,
    game_seconds_remaining: 900,
    qtr: 1,
    score_differential: 0,
  });

  const [prediction, setPrediction] = useState(null);
  const [pending, setPending] = useState({});
  const [playLog, setPlayLog] = useState([]);
  const [summary, setSummary] = useState({});

  const [actualPlayType, setActualPlayType] = useState("RUN");
  const [yardsGained, setYardsGained] = useState(0);

  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  const refreshData = async () => {
    try {
      const pendingRes = await fetch(`${API}/pending`);
      const playLogRes = await fetch(`${API}/play-log`);
      const summaryRes = await fetch(`${API}/summary`);

      const pendingData = await pendingRes.json();
      const playLogData = await playLogRes.json();
      const summaryData = await summaryRes.json();

      setPending(pendingData);
      setPlayLog(playLogData);
      setSummary(summaryData);
    } catch (error) {
      console.error("Error refreshing data:", error);
    }
  };

  useEffect(() => {
    refreshData();

    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleSetTeams = async () => {
    try {
      const res = await fetch(`${API}/set-teams`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ offense, defense }),
      });

      if (res.ok) {
        setTeamsSet(true);
      }
    } catch (error) {
      console.error("Error setting teams:", error);
    }
  };

  const handlePredict = async () => {
    try {
      const res = await fetch(`${API}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await res.json();
      setPrediction(data);
      refreshData();
    } catch (error) {
      console.error("Error predicting play:", error);
    }
  };

  const handleLogPlay = async () => {
    try {
      const res = await fetch(`${API}/log-play`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          actual_play_type: actualPlayType,
          yards_gained: Number(yardsGained),
        }),
      });

      if (res.ok) {
        setPrediction(null);
        setYardsGained(0);
        refreshData();
      }
    } catch (error) {
      console.error("Error logging play:", error);
    }
  };

  const handleNewDrive = async () => {
    try {
      await fetch(`${API}/new-drive`, {
        method: "POST",
      });
      refreshData();
    } catch (error) {
      console.error("Error starting new drive:", error);
    }
  };

  const formatPct = (value) => {
    if (value == null) return "N/A";
    return `${(value * 100).toFixed(1)}%`;
  };

  const getConfidenceColor = (tier) => {
    if (tier === "HIGH" || tier === "STRONG") return "#22c55e";
    if (tier === "MODERATE") return "#f59e0b";
    return "#ef4444";
  };

  const styles = {
    page: {
      minHeight: "100vh",
      background:
        "linear-gradient(180deg, #000000 0%, #000000 45%, #080808 100%)",
      color: "#f5f5f5",
      fontFamily: "Arial, sans-serif",
      padding: isMobile ? "16px" : "28px",
    },
    container: {
      maxWidth: "1400px",
      margin: "0 auto",
    },
    hero: {
      background:
        "linear-gradient(135deg, rgba(62, 136, 68, 0.86), rgba(32, 31, 31, 0.99))",
      border: "1px solid rgba(255, 255, 255, 0.18)",
      borderRadius: "20px",
      padding: isMobile ? "20px" : "28px",
      marginBottom: "24px",
      boxShadow: "0 20px 40px rgba(106, 102, 102, 0.56)",
    },
    heroTitle: {
      fontSize: isMobile ? "30px" : "44px",
      fontWeight: "800",
      margin: 0,
      color: "#0b0b0b",
      wordBreak: "break-word",
      lineHeight: isMobile ? "1.1" : "normal",
    },
    heroSubtitle: {
      marginTop: "10px",
      fontSize: isMobile ? "14px" : "16px",
      color: "#0f0f0f",
      wordBreak: "break-word",
      lineHeight: "1.4",
    },
    sectionTitle: {
      fontSize: isMobile ? "20px" : "22px",
      fontWeight: "800",
      color: "#f8fafc",
      marginBottom: "18px",
      marginTop: 0,
      wordBreak: "break-word",
    },
    card: {
      background: "rgba(0, 0, 0, 1)",
      border: "1px solid rgba(220, 226, 220, 0.16)",
      borderRadius: "18px",
      padding: isMobile ? "18px" : "22px",
      boxShadow: "0 12px 32px rgba(153, 227, 141, 0.22)",
      backdropFilter: "blur(6px)",
      minWidth: 0,
    },
    grid2: {
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr" : "1.15fr 0.85fr",
      gap: "20px",
      marginBottom: "20px",
    },
    grid3: {
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr" : "repeat(3, minmax(0, 1fr))",
      gap: "16px",
    },
    statGrid: {
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(4, minmax(0, 1fr))",
      gap: "14px",
      marginBottom: "20px",
    },
    statCard: {
      background: "linear-gradient(180deg, #000000, #000000)",
      border: "1px solid rgba(255, 255, 255, 0.16)",
      borderRadius: "16px",
      padding: isMobile ? "14px" : "16px",
      minWidth: 0,
    },
    statLabel: {
      fontSize: isMobile ? "11px" : "12px",
      color: "#dbd3d3",
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      marginBottom: "8px",
      wordBreak: "break-word",
    },
    statValue: {
      fontSize: isMobile ? "22px" : "28px",
      fontWeight: "800",
      color: "#f8fafc",
      wordBreak: "break-word",
    },
    label: {
      display: "block",
      fontSize: "13px",
      fontWeight: "700",
      color: "#909192",
      marginBottom: "8px",
      wordBreak: "break-word",
    },
    input: {
      width: "100%",
      padding: "12px 14px",
      borderRadius: "12px",
      border: "1px solid rgba(29, 29, 29, 0.25)",
      background: "#121312",
      color: "#f8fafc",
      fontSize: isMobile ? "16px" : "15px",
      outline: "none",
      boxSizing: "border-box",
      minWidth: 0,
    },
    buttonPrimary: {
      padding: "12px 18px",
      borderRadius: "12px",
      border: "none",
      background: "linear-gradient(135deg, #25eb2c, #1dd81d)",
      color: "#000000",
      fontWeight: "700",
      cursor: "pointer",
      boxShadow: "0 10px 20px rgba(9, 59, 13, 0.25)",
      width: isMobile ? "100%" : "auto",
    },
    buttonSecondary: {
      padding: "12px 18px",
      borderRadius: "12px",
      border: "1px solid rgba(255, 255, 255, 0.47)",
      background: "#000000",
      color: "#2fc50e",
      fontWeight: "700",
      cursor: "pointer",
      width: isMobile ? "100%" : "auto",
    },
    buttonRow: {
      display: "flex",
      gap: "12px",
      marginTop: "18px",
      flexWrap: "wrap",
      flexDirection: isMobile ? "column" : "row",
    },
    badge: {
      display: "inline-block",
      padding: "6px 10px",
      borderRadius: "999px",
      fontSize: "12px",
      fontWeight: "800",
      letterSpacing: "0.05em",
      marginLeft: isMobile ? "0" : "10px",
      marginTop: isMobile ? "10px" : "0",
    },
    predictionBig: {
      fontSize: isMobile ? "30px" : "40px",
      fontWeight: "900",
      color: "#f8fafc",
      margin: "0 0 8px 0",
      wordBreak: "break-word",
      lineHeight: isMobile ? "1.1" : "normal",
    },
    predictionMeta: {
      color: "#94b899",
      fontSize: isMobile ? "13px" : "14px",
      marginBottom: "18px",
      wordBreak: "break-word",
    },
    metricRow: {
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
      gap: "12px",
      marginBottom: "18px",
    },
    metricBox: {
      background: "#0b200b",
      border: "1px solid rgba(26, 26, 27, 0.14)",
      borderRadius: "14px",
      padding: "14px",
      minWidth: 0,
    },
    metricLabel: {
      fontSize: "12px",
      color: "#ffffff",
      marginBottom: "8px",
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      wordBreak: "break-word",
    },
    metricValue: {
      fontSize: isMobile ? "22px" : "26px",
      fontWeight: "800",
      color: "#f8fafc",
      wordBreak: "break-word",
    },
    strategyGrid: {
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
      gap: "12px",
      marginTop: "14px",
    },
    strategyItem: {
      background: "#34552d",
      borderRadius: "12px",
      padding: "12px",
      border: "1px solid rgba(255, 248, 248, 0.7)",
      minWidth: 0,
    },
    strategyLabel: {
      fontSize: "12px",
      color: "#000000",
      marginBottom: "6px",
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      wordBreak: "break-word",
    },
    strategyValue: {
      fontWeight: "700",
      color: "#f8fafc",
      wordBreak: "break-word",
    },
    reasonBox: {
      marginTop: "12px",
      background: "rgba(37, 235, 60, 0.1)",
      border: "1px solid rgba(57, 58, 60, 0.22)",
      borderRadius: "12px",
      padding: "12px",
      color: "#dbeafe",
      wordBreak: "break-word",
      lineHeight: "1.4",
    },
    tableWrap: {
      overflowX: "auto",
      borderRadius: "16px",
      border: "1px solid rgba(7, 47, 8, 0.32)",
      WebkitOverflowScrolling: "touch",
    },
    table: {
      width: "100%",
      borderCollapse: "collapse",
      background: "#123004",
      minWidth: isMobile ? "700px" : "100%",
    },
    th: {
      textAlign: "left",
      padding: isMobile ? "10px" : "14px",
      color: "#c4c7ca",
      fontSize: isMobile ? "10px" : "12px",
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      borderBottom: "1px solid rgba(45, 56, 45, 0.54)",
      background: "#032003",
      whiteSpace: "nowrap",
    },
    td: {
      padding: isMobile ? "10px" : "14px",
      borderBottom: "1px solid rgba(26, 76, 33, 0.26)",
      color: "#e5e7eb",
      fontSize: isMobile ? "12px" : "14px",
      whiteSpace: isMobile ? "nowrap" : "normal",
    },
    empty: {
      color: "#0e3815",
      fontSize: "15px",
      margin: 0,
    },
    setupWrap: {
      minHeight: "100vh",
      background:
        "linear-gradient(180deg, #171e19 0%, #6bac6d 45%, #131b14 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: isMobile ? "16px" : "24px",
      fontFamily: "Arial, sans-serif",
    },
    setupCard: {
      width: "100%",
      maxWidth: "720px",
      background: "rgba(49, 61, 49, 0.92)",
      border: "1px solid rgba(89, 90, 93, 0.16)",
      borderRadius: "22px",
      padding: isMobile ? "20px" : "30px",
      boxShadow: "0 20px 50px rgba(233, 234, 232, 0.3)",
      minWidth: 0,
    },
    setupTitle: {
      fontSize: isMobile ? "32px" : "42px",
      fontWeight: "900",
      color: "#f8fafc",
      margin: 0,
      wordBreak: "break-word",
      lineHeight: isMobile ? "1.1" : "normal",
    },
    setupSubtitle: {
      marginTop: "10px",
      color: "#000000",
      marginBottom: "24px",
      fontSize: isMobile ? "14px" : "16px",
      wordBreak: "break-word",
      lineHeight: "1.4",
    },
  };

  if (!teamsSet) {
    return (
      <div style={styles.setupWrap}>
        <div style={styles.setupCard}>
          <h1 style={styles.setupTitle}>
            Coordin<span style={{ color: "#0b0b0b" }}>AI</span>te
          </h1>
          <p style={styles.setupSubtitle}>
            Set the offense and defense to begin the live prediction dashboard.
          </p>

          <div style={styles.grid2}>
            <div>
              <label style={styles.label}>Offense Team</label>
              <input
                type="text"
                placeholder="ex. KC"
                value={offense}
                onChange={(e) => setOffense(e.target.value)}
                style={styles.input}
              />
            </div>

            <div>
              <label style={styles.label}>Defense Team</label>
              <input
                type="text"
                placeholder="ex. BUF"
                value={defense}
                onChange={(e) => setDefense(e.target.value)}
                style={styles.input}
              />
            </div>
          </div>

          <div style={styles.buttonRow}>
            <button onClick={handleSetTeams} style={styles.buttonPrimary}>
              Launch Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <div style={styles.hero}>
          <h1 style={styles.heroTitle}>Football AI Defensive Assistant</h1>
          <div style={styles.heroSubtitle}>
            Live play prediction, defensive recommendation, and in-game tracking
          </div>
        </div>

        <div style={styles.statGrid}>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Total Predictions</div>
            <div style={styles.statValue}>{summary.total_predictions ?? 0}</div>
          </div>

          <div style={styles.statCard}>
            <div style={styles.statLabel}>Game Accuracy</div>
            <div style={styles.statValue}>
              {formatPct(summary.game_accuracy)}
            </div>
          </div>

          <div style={styles.statCard}>
            <div style={styles.statLabel}>Last 5 Accuracy</div>
            <div style={styles.statValue}>
              {formatPct(summary.last_5_accuracy)}
            </div>
          </div>

          <div style={styles.statCard}>
            <div style={styles.statLabel}>Last 10 Accuracy</div>
            <div style={styles.statValue}>
              {formatPct(summary.last_10_accuracy)}
            </div>
          </div>
        </div>

        <div style={styles.grid2}>
          <div style={styles.card}>
            <h2 style={styles.sectionTitle}>Game Situation</h2>

            <div style={styles.grid3}>
              <div>
                <label style={styles.label}>Down</label>
                <input
                  type="number"
                  value={form.down}
                  onChange={(e) =>
                    setForm({ ...form, down: Number(e.target.value) })
                  }
                  style={styles.input}
                />
              </div>

              <div>
                <label style={styles.label}>Yards to Go</label>
                <input
                  type="number"
                  value={form.ydstogo}
                  onChange={(e) =>
                    setForm({ ...form, ydstogo: Number(e.target.value) })
                  }
                  style={styles.input}
                />
              </div>

              <div>
                <label style={styles.label}>Yardline (0-100)</label>
                <input
                  type="number"
                  value={form.yardline_100}
                  onChange={(e) =>
                    setForm({ ...form, yardline_100: Number(e.target.value) })
                  }
                  style={styles.input}
                />
              </div>

              <div>
                <label style={styles.label}>Game Seconds Remaining</label>
                <input
                  type="number"
                  value={form.game_seconds_remaining}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      game_seconds_remaining: Number(e.target.value),
                    })
                  }
                  style={styles.input}
                />
              </div>

              <div>
                <label style={styles.label}>Quarter</label>
                <input
                  type="number"
                  value={form.qtr}
                  onChange={(e) =>
                    setForm({ ...form, qtr: Number(e.target.value) })
                  }
                  style={styles.input}
                />
              </div>

              <div>
                <label style={styles.label}>Score Differential</label>
                <input
                  type="number"
                  value={form.score_differential}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      score_differential: Number(e.target.value),
                    })
                  }
                  style={styles.input}
                />
              </div>
            </div>

            <div style={styles.buttonRow}>
              <button onClick={handlePredict} style={styles.buttonPrimary}>
                Predict Next Play
              </button>
              <button onClick={handleNewDrive} style={styles.buttonSecondary}>
                Start New Drive
              </button>
            </div>
          </div>

          <div style={styles.card}>
            <h2 style={styles.sectionTitle}>Log Actual Play</h2>

            <div style={styles.grid2}>
              <div>
                <label style={styles.label}>Actual Play Type</label>
                <select
                  value={actualPlayType}
                  onChange={(e) => setActualPlayType(e.target.value)}
                  style={styles.input}
                >
                  <option value="RUN">RUN</option>
                  <option value="PASS">PASS</option>
                </select>
              </div>

              <div>
                <label style={styles.label}>Yards Gained</label>
                <input
                  type="number"
                  placeholder="0"
                  value={yardsGained}
                  onChange={(e) => setYardsGained(e.target.value)}
                  style={styles.input}
                />
              </div>
            </div>

            <div style={styles.buttonRow}>
              <button onClick={handleLogPlay} style={styles.buttonPrimary}>
                Save Play Result
              </button>
            </div>

            {pending && Object.keys(pending).length > 0 ? (
              <div style={styles.reasonBox}>
                A prediction is currently pending and ready to be logged.
              </div>
            ) : (
              <div style={styles.reasonBox}>
                No pending play yet. Run a prediction first.
              </div>
            )}
          </div>
        </div>

        {prediction && (
          <div style={{ ...styles.card, marginBottom: "20px" }}>
            <h2
              style={{
                ...styles.sectionTitle,
                display: "flex",
                flexDirection: isMobile ? "column" : "row",
                alignItems: isMobile ? "flex-start" : "center",
              }}
            >
              Prediction Result
              <span
                style={{
                  ...styles.badge,
                  background: `${getConfidenceColor(
                    prediction.confidence_tier
                  )}22`,
                  color: getConfidenceColor(prediction.confidence_tier),
                  border: `1px solid ${getConfidenceColor(
                    prediction.confidence_tier
                  )}55`,
                }}
              >
                {prediction.confidence_tier}
              </span>
            </h2>

            <div style={styles.predictionBig}>{prediction.prediction}</div>
            <div style={styles.predictionMeta}>
              Confidence: {(prediction.confidence * 100).toFixed(1)}%
            </div>

            <div style={styles.metricRow}>
              <div style={styles.metricBox}>
                <div style={styles.metricLabel}>Run Probability</div>
                <div style={styles.metricValue}>
                  {(prediction.run_probability * 100).toFixed(1)}%
                </div>
              </div>

              <div style={styles.metricBox}>
                <div style={styles.metricLabel}>Pass Probability</div>
                <div style={styles.metricValue}>
                  {(prediction.pass_probability * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {prediction.defensive_strategy && (
              <>
                <h3
                  style={{
                    color: "#f8fafc",
                    fontSize: isMobile ? "16px" : "18px",
                    marginBottom: "14px",
                    wordBreak: "break-word",
                  }}
                >
                  Recommended Defensive Strategy
                </h3>

                <div style={styles.strategyGrid}>
                  <div style={styles.strategyItem}>
                    <div style={styles.strategyLabel}>Personnel</div>
                    <div style={styles.strategyValue}>
                      {prediction.defensive_strategy.defensive_personnel}
                    </div>
                  </div>

                  <div style={styles.strategyItem}>
                    <div style={styles.strategyLabel}>Front</div>
                    <div style={styles.strategyValue}>
                      {prediction.defensive_strategy.front}
                    </div>
                  </div>

                  <div style={styles.strategyItem}>
                    <div style={styles.strategyLabel}>Coverage</div>
                    <div style={styles.strategyValue}>
                      {prediction.defensive_strategy.coverage_shell}
                    </div>
                  </div>

                  <div style={styles.strategyItem}>
                    <div style={styles.strategyLabel}>Pressure</div>
                    <div style={styles.strategyValue}>
                      {prediction.defensive_strategy.pressure}
                    </div>
                  </div>

                  <div style={styles.strategyItem}>
                    <div style={styles.strategyLabel}>Aggression</div>
                    <div style={styles.strategyValue}>
                      {prediction.defensive_strategy.aggression}
                    </div>
                  </div>

                  <div style={styles.strategyItem}>
                    <div style={styles.strategyLabel}>Primary Focus</div>
                    <div style={styles.strategyValue}>
                      {prediction.defensive_strategy.primary_focus}
                    </div>
                  </div>
                </div>

                <div style={styles.reasonBox}>
                  <strong>Reason:</strong>{" "}
                  {prediction.defensive_strategy.reason}
                </div>
              </>
            )}
          </div>
        )}

        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Play Log</h2>

          {playLog.length === 0 ? (
            <p style={styles.empty}>No plays logged yet.</p>
          ) : (
            <div style={styles.tableWrap}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>#</th>
                    <th style={styles.th}>Predicted</th>
                    <th style={styles.th}>Actual</th>
                    <th style={styles.th}>Correct</th>
                    <th style={styles.th}>Confidence</th>
                    <th style={styles.th}>Yards</th>
                    <th style={styles.th}>Drive</th>
                  </tr>
                </thead>
                <tbody>
                  {playLog.map((play, index) => (
                    <tr key={index}>
                      <td style={styles.td}>{index + 1}</td>
                      <td style={styles.td}>{play.predicted_play_type}</td>
                      <td style={styles.td}>{play.actual_play_type}</td>
                      <td style={styles.td}>
                        {play.correct_prediction ? "Yes" : "No"}
                      </td>
                      <td style={styles.td}>{formatPct(play.confidence)}</td>
                      <td style={styles.td}>{play.yards_gained}</td>
                      <td style={styles.td}>{play.drive_number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;

