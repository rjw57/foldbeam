#ifndef PJ_TSFN_H__
#define PJ_TSFN_H__
#include "constants.h"
float
pj_tsfn(float phi, float sinphi, float e) {
	sinphi *= e;
	return (tan (.5 * (HALFPI - phi)) /
	   pow((1. - sinphi) / (1. + sinphi), .5 * e));
}
#endif /* PJ_TSFN_H__ */
