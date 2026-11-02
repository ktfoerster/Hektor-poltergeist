// Accelerated *untrusted* first-failing-walk discovery. The independent
// lasso_witness.py checker must verify EACH emitted witness before it is used.
// This program does not alter verify.cpp or certify full graph positivity.
#include <algorithm>
#include <array>
#include <climits>
#include <fstream>
#include <iostream>
#include <numeric>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace std;

namespace {
using Step = array<int, 5>; // vertex, local_live, incoming, bit, action
struct Witness {int mask, source, cycle_start; vector<Step> steps;};
int table[7][128][8][2];

void fail(const string &msg) { throw runtime_error(msg); }

struct Graph {
 int n, target, full_mask;
 vector<pair<int,int>> edges;
 array<int,7> host{};
 Graph(int size, int t):n(size), target(t) {
   if(n<2||n>7||t<0||t>=n)fail("invalid graph header");
   for(int u=0;u<n;u++)for(int v=u+1;v<n;v++) {
     if(n==7&&((u==3&&v==4)||(u==5&&v==6)))continue;
     edges.emplace_back(u,v);host[u]|=1<<v;host[v]|=1<<u;
   }
   full_mask=(1<<edges.size())-1;
 }
 array<int,7> adj(int mask) const {
   array<int,7> a{};
   for(size_t j=0;j<edges.size();j++) if(mask&(1<<j)) {
     auto [u,v]=edges[j];a[u]|=1<<v;a[v]|=1<<u;
   }
   return a;
 }
 int connected(const array<int,7>&adj) const {
   int c=1<<target,old;
   do {old=c;for(int v=0;v<n;v++)if(c&(1<<v))c|=adj[v];} while(c!=old);
   return c;
 }
};

Graph read_policy(const string &path){
 ifstream f(path);
 int n,t;
 if(!(f>>n>>t))fail("missing policy header");
 Graph g(n,t);
 for(auto &a:table)for(auto &b:a)for(auto &c:b)for(int &d:c)d=-1;
 int u,L,p,b,x;
 while(f>>u){
  if(!(f>>L>>p>>b>>x))fail("truncated policy row");
  if(u<0||u>=g.n||u==g.target||L<=0||L>=(1<<g.n)||
     (L&~g.host[u])||p< -1||p>=g.n||b<0||b>1||
     (p==-1&&b!=0)||(p>=0&&!(L&(1<<p)))||
     x<0||x>=2*g.n||!(L&(1<<(x/2)))||
     ((L&(1<<g.target))&&x!=2*g.target))fail("illegal or non-normalized policy row");
  int &slot=table[u][L][p+1][b];
  if(slot!=-1)fail("duplicate policy row");
  slot=x;
 }
 if(!f.eof())fail("trailing malformed policy input");
 for(u=0;u<g.n;u++)if(u!=g.target)for(L=1;L<(1<<g.n);L++) {
  if(L&~g.host[u])continue;
  if(table[u][L][0][0]<0)fail("missing source injection");
  for(int p=0;p<g.n;p++)if(L&(1<<p))for(int b=0;b<2;b++)
    if(table[u][L][p+1][b]<0)fail("missing transit row");
 }
 return g;
}

vector<int> read_masks(const string &path, int maximum){
 ifstream f(path);
 if(!f)fail("could not read masks file");
 long long value;
 vector<int> masks;
 while(f>>value){
  if(value<0||value>maximum||(!masks.empty()&&value<=masks.back()))
    fail("mask must be in range and strictly ascending");
  masks.push_back(static_cast<int>(value));
  if(masks.size()>524288)fail("mask count exceeds graph maximum");
 }
 if(!f.eof()||masks.empty())fail("malformed or empty mask stream");
 return masks;
}

bool failing_walk(const Graph&g,const array<int,7>&adj,int mask,int source,Witness&out){
 // Recording seen arrival configurations, not vertices. Source revisits are legal.
 int seen[7][7][2];
 for(auto &a:seen)for(auto &b:a)for(int &c:b)c=-1;
 int u=source, incoming=-1, bit=0;
 vector<Step> steps;
 while(u!=g.target){
  if(incoming>=0){
   if(seen[u][incoming][bit]>=0){
    out={mask,source,seen[u][incoming][bit],std::move(steps)};
    return true;
   }
   seen[u][incoming][bit]=static_cast<int>(steps.size());
  }
  int action=table[u][adj[u]][incoming+1][bit];
  if(action<0||!(adj[u]&(1<<(action/2))))fail("invalid selected port");
  steps.push_back({u,adj[u],incoming,bit,action});
  incoming=u;u=action/2;bit=action&1;
  if(steps.size()>1+2*7*6)fail("state bound exceeded");
 }
 return false;
}

vector<Step> selector_signature(const Witness&w){
 vector<Step> key=w.steps;
 sort(key.begin(),key.end());
 key.erase(unique(key.begin(),key.end()),key.end());
 return key;
}
// A candidate is always a fully source-reachable, locally deterministic lasso.
// This selection is HEURISTIC ONLY: dropping one necessary clause does not
// constrain or change the legal routing-policy space.
struct Candidate { Witness witness; vector<Step> signature; };

// A shorter negative-selector clause subsumes a longer one when its selected
// routing actions form a subset. Both arguments use canonical Step ordering.
bool subsumed(const vector<Step> &stronger, const vector<Step> &weaker){
 return includes(weaker.begin(),weaker.end(),stronger.begin(),stronger.end());
}

vector<Candidate> select_short_diverse(vector<Candidate> pool,int limit){
 vector<int> order(pool.size());
 iota(order.begin(),order.end(),0);
 sort(order.begin(),order.end(),[&](int i,int j){
  const auto &a=pool[i],&b=pool[j];
  if(a.signature.size()!=b.signature.size())return a.signature.size()<b.signature.size();
  if(a.witness.steps.size()!=b.witness.steps.size())return a.witness.steps.size()<b.witness.steps.size();
  if(a.witness.mask!=b.witness.mask)return a.witness.mask<b.witness.mask;
  return a.witness.source<b.witness.source;
 });
 // Remove only locally redundant consequences, never a possible legal policy.
 vector<int> nonredundant;
 for(int i:order){
  bool weak=false;
  for(int j:nonredundant)
   if(subsumed(pool[j].signature,pool[i].signature)){weak=true;break;}
  if(!weak)nonredundant.push_back(i);
 }
 int count=min(limit,static_cast<int>(nonredundant.size()));
 vector<int> chosen;
 vector<char> selected(pool.size(),false);
 int short_quota=(count+1)/2;
 for(int p=0;p<short_quota;p++){
  int i=nonredundant[p];chosen.push_back(i);selected[i]=true;
 }
 // Diversify exact static failure masks, NOT packet state or routing actions.
 // Maximize Hamming distance to the nearest selected residual, breaking ties
 // by shorter clause and then deterministic source/mask order.
 while(static_cast<int>(chosen.size())<count){
  int best=-1, best_distance=-1;
  for(int i:nonredundant){
   if(selected[i])continue;
   int nearest=numeric_limits<int>::max();
   for(int j:chosen){
    int distance=__builtin_popcount(static_cast<unsigned>(pool[i].witness.mask^pool[j].witness.mask));
    nearest=min(nearest,distance);
   }
   if(best<0||nearest>best_distance||
      (nearest==best_distance &&
       (pool[i].signature.size()<pool[best].signature.size()||
        (pool[i].signature.size()==pool[best].signature.size()&&
         (pool[i].witness.mask<pool[best].witness.mask||
          (pool[i].witness.mask==pool[best].witness.mask&&
           pool[i].witness.source<pool[best].witness.source)))))){
    best=i;best_distance=nearest;
   }
  }
  if(best<0)fail("short-diverse selection exhausted candidate pool");
  selected[best]=true;chosen.push_back(best);
 }
 vector<Candidate> answer;
 for(int i:chosen)answer.push_back(std::move(pool[i]));
 return answer;
}
void print_witness(const Witness&w){
 cout<<"{\"type\":\"witness\",\"witness\":{\"schema\":1,\"mask\":"<<w.mask
     <<",\"source\":"<<w.source<<",\"cycle_start\":"<<w.cycle_start
     <<",\"steps\":[";
 for(size_t i=0;i<w.steps.size();i++){
  if(i)cout<<',';
  cout<<'[';
  for(int j=0;j<5;j++){if(j)cout<<',';cout<<w.steps[i][j];}
  cout<<']';
 }
 cout<<"]}}\n";
}
} // namespace

int main(int argc,char**argv) {
 try {
  if(argc!=4&&argc!=5)fail("usage: lasso_batch POLICY.tsv SORTED_MASKS.txt MAX_WITNESSES [first|short-diverse]");
  const string selection=(argc==5?argv[4]:"first");
  if(selection!="first"&&selection!="short-diverse")fail("invalid witness selection mode");
  string limitarg=argv[3];
  if(limitarg.empty()||limitarg.find_first_not_of("0123456789")!=string::npos)
    fail("invalid witness bound");
  int limit=stoi(limitarg);
  if(limit<1||limit>2048)fail("witness bound outside 1..2048");
  Graph g=read_policy(argv[1]);
  auto masks=read_masks(argv[2],g.full_mask);
  set<vector<Step>> signatures;
  int scanned=0,failed_masks=0,connected_obligations=0,witnesses=0;
  size_t examined_candidates=0;
  if(selection=="first"){
   // Bit-for-bit legacy traversal and early stopping remain the control.
   for(int mask:masks){
    auto a=g.adj(mask);
    int component=g.connected(a);
    scanned++;
    Witness bad;
    bool found=false;
    for(int source=0;source<g.n;source++){
     if(source==g.target||!(component&(1<<source)))continue;
     connected_obligations++;
     if(!found&&failing_walk(g,a,mask,source,bad))found=true;
    }
    if(found){
     failed_masks++;
     if(signatures.insert(selector_signature(bad)).second){
      print_witness(bad);witnesses++;
      if(witnesses>=limit)break;
     }
    }
   }
  } else {
   // Scan the ENTIRE fixed residual suite, checking every connected source.
   // The winning source per residual minimizes distinct selected actions.
   // Keep one canonical representative per distinct global selector signature.
   vector<Candidate> pool;
   for(int mask:masks){
    const auto a=g.adj(mask);
    const int component=g.connected(a);
    scanned++;
    bool found=false;
    Candidate best{};
    for(int source=0;source<g.n;source++){
     if(source==g.target||!(component&(1<<source)))continue;
     connected_obligations++;
     Witness candidate;
     if(!failing_walk(g,a,mask,source,candidate))continue;
     auto signature=selector_signature(candidate);
     if(!found||signature.size()<best.signature.size()||
        (signature.size()==best.signature.size()&&
         candidate.steps.size()<best.witness.steps.size())){
      best={std::move(candidate),std::move(signature)};
     }
     found=true;
    }
    if(found){
     failed_masks++;
     if(signatures.insert(best.signature).second){
      pool.push_back(std::move(best));
     }
    }
   }
   examined_candidates=pool.size();
   for(auto &candidate:select_short_diverse(std::move(pool),limit)){
    print_witness(candidate.witness);
    witnesses++;
   }
  }
  cout<<"{\"type\":\"summary\",\"schema\":1,\"n\":"<<g.n
      <<",\"target\":"<<g.target<<",\"scanned_masks\":"<<scanned
      <<",\"total_masks\":"<<masks.size()
      <<",\"scan_complete\":"<<(scanned==(int)masks.size()?"true":"false")
      <<",\"connected_source_obligations\":"<<connected_obligations
      <<",\"failed_masks\":"<<failed_masks
      <<",\"witnesses\":"<<witnesses;
  if(selection=="short-diverse"){
    cout<<",\"selection\":\"short-diverse\""
        <<",\"unique_candidates\":"<<examined_candidates;
  }
  cout<<"}\n";
 } catch(const exception&e){cerr<<e.what()<<'\n';return 2;}
}
