const LABELS = {
  switch: "Công tắc",
  light: "Đèn",
  socket: "Ổ cắm",
  distribution_board: "Tủ điện (DB)",
  breaker: "MCB/Aptomat",
  equipment: "Thiết bị",
};

export default function TypeBreakdown({ byType }) {
  const entries = Object.entries(byType || {}).sort((a, b) => b[1] - a[1]);
  return (
    <div className="section">
      <h2>Phân loại đối tượng</h2>
      <table>
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k}>
              <td><span className={`badge ${k}`}>{k}</span></td>
              <td className="muted">{LABELS[k] || k}</td>
              <td style={{ textAlign: "right", fontWeight: 600 }}>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
