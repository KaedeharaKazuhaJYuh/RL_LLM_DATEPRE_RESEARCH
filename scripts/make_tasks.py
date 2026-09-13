from research.benchmark import build
if __name__=='__main__':
    tasks,_=build();print(f'generated {len(tasks)} v2 tasks')
