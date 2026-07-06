export default function StatsCards({ stats }) {
  const cards = [
    { l: "Trang", v: stats.pages },
    { l: "Đối tượng", v: stats.nodes },
    { l: "Nối dây (topology)", v: stats.connected_to },
    { l: "Quan hệ suy luận", v: stats.relationships },
    { l: "Liên kết chéo sheet", v: stats.cross_ref },
  ];
  return (
    <div className="cards">
      {cards.map((c) => (
        <div className="card" key={c.l}>
          <div className="v">{c.v ?? 0}</div>
          <div className="l">{c.l}</div>
        </div>
      ))}
    </div>
  );
}
