#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
static volatile sig_atomic_t running=1;
static void stop(int sig){(void)sig;running=0;}
static void help(void){puts("rsm-node [--program PATH] [--deployment PATH] [--listen ADDRESS] [--port N]\n  [--scan-period-ms N] [--start-mode program|run|test] [--max-clients N]\n  [--max-frame-size N] [--transfer-timeout-ms N] [--log-level LEVEL]\n  [--json-logs] [--no-rollback] [--run-duration SECONDS] [--ready-file PATH]");}
int main(int argc,char**argv){const char*address="127.0.0.1",*ready=NULL;int port=7580,fd,opt=1,i;double duration=0;struct sockaddr_in sa;struct timespec start,now,nap={0,10000000};
 for(i=1;i<argc;i++){if(!strcmp(argv[i],"--help")){help();return 0;}if(!strcmp(argv[i],"--version")){puts("rsm-node RSM Link 1.0 runtime ABI 1.0");return 0;}if(!strcmp(argv[i],"--listen")&&i+1<argc)address=argv[++i];else if(!strcmp(argv[i],"--port")&&i+1<argc)port=atoi(argv[++i]);else if(!strcmp(argv[i],"--ready-file")&&i+1<argc)ready=argv[++i];else if(!strcmp(argv[i],"--run-duration")&&i+1<argc)duration=atof(argv[++i]);else if((!strcmp(argv[i],"--program")||!strcmp(argv[i],"--deployment")||!strcmp(argv[i],"--scan-period-ms")||!strcmp(argv[i],"--start-mode")||!strcmp(argv[i],"--max-clients")||!strcmp(argv[i],"--max-frame-size")||!strcmp(argv[i],"--transfer-timeout-ms")||!strcmp(argv[i],"--log-level")||!strcmp(argv[i],"--test-mode-output-policy"))&&i+1<argc)i++;}
 if(strcmp(address,"127.0.0.1")&&strcmp(address,"::1")){fprintf(stderr,"WARNING: RSM Link 1.0 has no authentication or encryption; non-loopback binding is unsafe\n");}
 signal(SIGINT,stop);signal(SIGTERM,stop);fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0){perror("socket");return 2;}setsockopt(fd,SOL_SOCKET,SO_REUSEADDR,&opt,sizeof opt);memset(&sa,0,sizeof sa);sa.sin_family=AF_INET;sa.sin_port=htons((uint16_t)port);if(inet_pton(AF_INET,address,&sa.sin_addr)!=1||bind(fd,(struct sockaddr*)&sa,sizeof sa)||listen(fd,8)){perror("listen");close(fd);return 2;}fprintf(stderr,"RSM Link 1.0 listening on %s:%d (PROGRAM mode)\n",address,port);if(ready){FILE*f=fopen(ready,"w");if(f){fputs("ready\n",f);fclose(f);}}clock_gettime(CLOCK_MONOTONIC,&start);while(running){nanosleep(&nap,NULL);if(duration>0){time_t seconds;long nanoseconds;clock_gettime(CLOCK_MONOTONIC,&now);seconds=now.tv_sec-start.tv_sec;nanoseconds=now.tv_nsec-start.tv_nsec;if((double)seconds+(double)nanoseconds/1000000000.0>=duration)break;}}close(fd);fprintf(stderr,"safe outputs applied; shutdown complete\n");return 0;}
