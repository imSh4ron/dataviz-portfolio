import pandas as pd, re
r=pd.read_csv('MARPP_MSA_2008_2024.csv',encoding='latin1',dtype=str)
r=r[r.Description.str.strip()=="RPPs: All items"]
r=r[r.GeoName.str.contains("Metropolitan Statistical Area")]
r["MSA"]=r.GeoName.str.replace(r"\s*\(Metropolitan Statistical Area\).*","",regex=True).str.strip()
r["RPP"]=r["2024"].astype(float)
idx={}
for m in r.MSA:
    cities,states=m.rsplit(", ",1)
    for c in cities.split("-"):
        for s in states.split("-"): idx[(c.strip().lower(),s.strip())]=m
# suburbs -> principal city of their metro
sub={"mountain view":"san jose","palo alto":"san jose","menlo park":"san francisco","cupertino":"san jose","milpitas":"san jose","los gatos":"san jose","foster city":"san francisco","south san francisco":"san francisco","redwood city":"san francisco","san mateo":"san francisco","san bruno":"san francisco",
"redmond":"seattle","bothell":"seattle","kirkland":"seattle","culver city":"los angeles","santa monica":"los angeles","irvine":"anaheim",
"plano":"dallas","irving":"dallas","frisco":"dallas","mckinney":"dallas","richardson":"dallas","fort worth":"dallas","cresson":"fort worth",
"jersey city":"new york","whippany":"new york","whitehouse station":"new york","brooklyn":"new york",
"mclean":"washington","vienna":"washington","reston":"washington","herndon":"washington","tysons":"washington",
"cambridge":"boston","riverwoods":"chicago","schaumburg":"chicago","malvern":"philadelphia","alpharetta":"atlanta","collierville":"memphis","hillsboro":"portland","dearborn":"detroit","cary":"raleigh","bentonville":"fayetteville","rogers":"fayetteville","tempe":"phoenix","scottsdale":"phoenix","chandler":"phoenix","long island city":"new york","cumming":"atlanta","aubrey":"dallas","westlake":"dallas","lewisville":"dallas","denton":"dallas","coppell":"dallas","morrisville":"raleigh","waltham":"boston","burlington":"boston","edison":"new york","iselin":"new york","piscataway":"new york","newark":"new york","hoboken":"new york","leander":"austin","overland park":"kansas city","santa clara":"san jose","sunnyvale":"san jose","bellevue":"seattle","arlington":"washington","bethesda":"washington","oakland":"san francisco","fremont":"san francisco","emeryville":"san francisco"}
st_of={"cresson":"TX"}
def msa(row):
    c=str(row.CITY).rsplit(", ",1);city=c[0].lower();st=c[1] if len(c)>1 else ""
    city=sub.get(city,city)
    return idx.get((city,st)) or (idx.get((city,"NJ")) if st=="NJ" else None) or next((m for (cc,ss),m in idx.items() if cc==city and m.endswith(st)),None)
d=pd.read_csv("lca_data_jobs_clean.csv",dtype={"NAICS_CODE":str})
d["MSA"]=d.apply(msa,axis=1)
print(f"matched {d.MSA.notna().mean():.1%} of rows")
d=d.merge(r[["MSA","RPP"]],on="MSA",how="left")
d["ADJ_SALARY"]=d.SALARY/d.RPP*100
d.to_csv("lca_with_metro.csv",index=False)
m=d.groupby("MSA").agg(jobs=("SALARY","size"),median_salary=("SALARY","median"),rpp=("RPP","first"),median_adj=("ADJ_SALARY","median")).query("jobs>=90").sort_values("median_adj",ascending=False)
m.to_csv("summary_by_metro.csv")
pd.set_option("display.width",200);print(m.round(0).to_string())
print(d[d.MSA.isna()].CITY.value_counts().head(15))
