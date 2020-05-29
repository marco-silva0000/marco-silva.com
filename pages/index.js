import Head from 'next/head'
import Link from 'next/link'
import fs from 'fs';
import path from 'path';
import matter from "gray-matter";
import Col from 'react-bootstrap/Col'
import Row from 'react-bootstrap/Row'
import Container from 'react-bootstrap/Container'
import ListGroup from 'react-bootstrap/ListGroup'
import Image from 'react-bootstrap/Image'

const Home = ({ posts, links }) => {
  return (
    <div className="container">
      <Head>
        <title>Marco Silva</title>
        <link rel="icon" href="/favicon.ico" />
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
      </Head>

      <main>
        <Container>
          <Row className="align-items-center justify-content-cente">
            <Col className="text-center">
              <h1 className="text-center">Hello</h1>
              <Image roundedCircle height="200" width="200" src="avatar.png" />
              <p className="description">My name is Marco Silva.</p>
              {links.map(props => ImageLinkComponent(props))}
              <ListGroup variant="flush">
                {posts.map(post => BlogLinkComponent(post))}
              </ListGroup>
            </Col>
          </Row>
        </Container>
      </main>

      <footer>
      </footer>
    </div>
  )
}

const ImageLinkComponent = ({ url, name, imgUrl }) => {
  return (
    <Link key={name} href={url}>
      <a href={url}>
        <img height="42" width="42" src={imgUrl} />
      </a>
    </Link>
  )
}

const BlogLinkComponent = ({slug, metaData}) => {
  return (
    <ListGroup.Item key={slug} action href={'/posts/' + slug}>
      {metaData.title} - <small className="text-muted">{metaData.description}</small>
    </ListGroup.Item>
  )
}

const getPosts = () => {
  const slugs = fs.readdirSync('posts').map(filename => filename.replace('.md', ''))
  let posts = slugs.map(slug => {
    const metaData = matter(fs.readFileSync(path.join('posts', slug + '.md')).toString()).data
    return {
      slug,
      metaData,
    }
  })
  console.log(posts)
  posts = posts.sort((a, b) => b.metaData.date.localeCompare(a.metaData.date))
  console.log(posts)
  return posts
}

const getLinks = () => {
  return [
    {"url": "https://twitter.com/marcosilva0000", "name": "Twitter", "imgUrl": "Twitter_Logo_Blue.png"},
    {"url": "https://www.linkedin.com/in/marco-silva-665793140/", "name": "LinkedIn", "imgUrl": "LI_Logo.png"},
    {"url": "https://github.com/marco-silva0000", "name": "Github", "imgUrl": "Github.png"}
  ]

}

export const getStaticProps = async () => {

  const links = getLinks()
  const posts = getPosts()
  
  return {
    props: {
      links,
      posts,
    }
  }
}

export default Home
