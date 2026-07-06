export default function RelationshipPanel({ relationships }) {
  return (
    <div className="section">
      <h2>Quan hệ suy luận (Rule Engine) — {relationships.length}</h2>
      {relationships.length === 0 ? (
        <p className="muted">Chưa suy ra quan hệ nào.</p>
      ) : (
        <div style={{ maxHeight: 360, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Rule</th>
                <th>Chủ thể</th>
                <th>Quan hệ</th>
                <th>Đối tượng</th>
              </tr>
            </thead>
            <tbody>
              {relationships.map((r, i) => (
                <tr key={i}>
                  <td className="muted">{r.rule}</td>
                  <td><strong>{r.subject}</strong></td>
                  <td><span className={`badge ${r.relation}`}>{r.relation}</span></td>
                  <td>{r.objects.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
