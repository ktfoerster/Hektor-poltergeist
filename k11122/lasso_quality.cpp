// Fast *untrusted* complete-frozen-suite policy-quality score.
// Reuse the exact deterministic walker compiled with the lasso scanner.
// Best-policy selection is diagnostic only; the Python independent literal
// replay must recheck every reported best before publication.
#define main lasso_batch_reference_cli
#include "lasso_batch.cpp"
#undef main

int main(int argc, char** argv) {
 try {
  if(argc!=3)fail("usage: lasso_quality POLICY.tsv SORTED_MASKS.txt");
  Graph g=read_policy(argv[1]);
  const auto masks=read_masks(argv[2],g.full_mask);
  long long obligations=0,failed_sources=0;
  int failed_masks=0;
  for(int mask:masks){
   const auto adj=g.adj(mask);
   const int connected=g.connected(adj);
   bool mask_failed=false;
   for(int source=0;source<g.n;source++){
    if(source==g.target||!(connected&(1<<source)))continue;
    obligations++;
    Witness witness;
    if(failing_walk(g,adj,mask,source,witness)){
     failed_sources++;
     mask_failed=true;
    }
   }
   if(mask_failed)failed_masks++;
  }
  cout<<"{\"schema\":1,\"type\":\"frozen_policy_quality\","
      <<"\"n\":"<<g.n
      <<",\"target\":"<<g.target
      <<",\"residuals\":"<<masks.size()
      <<",\"connected_source_obligations\":"<<obligations
      <<",\"failed_connected_sources\":"<<failed_sources
      <<",\"failing_residual_masks\":"<<failed_masks
      <<"}\n";
 }catch(const exception&e){cerr<<e.what()<<'\n';return 2;}
}
